"""Fizzco Migration Assurance Hub: tab 1 recon status, tab 2 ask the data (Genie), tab 3 ask the runbooks (RAG).

The app runs as its own service principal; Databricks supplies the credentials. Synthetic data only.
"""
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import streamlit as st
import databricks.sdk
from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from databricks.sdk.errors import DatabricksError
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

import helpers as H

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
LOGGER = logging.getLogger("fizzco_hub")
LOGGER.info("databricks-sdk version %s", databricks.sdk.version.__version__)

REGION_QUERY = (
    "SELECT current_user() AS signed_in_as, region, COUNT(*) AS rows_visible, "
    "ROUND(SUM(sell_in_net_amount), 2) AS net_sell_in "
    "FROM workspace.fizzco.gold_sell_in_vs_sell_out GROUP BY region ORDER BY region"
)
RECON_QUERY = (
    "SELECT recon_id, job_id, feed, recon_date, source_rows, trusted_rows, diff_rows, status "
    "FROM workspace.fizzco.gold_recon_results ORDER BY recon_date DESC, recon_id"
)
TOP_K = 5  # recommended in Scenario 4.5 (first relevant chunk was within rank 3 for 5 of 5 questions)
GENIE_TIMEOUT = timedelta(seconds=180)
CHAT_MAX_TOKENS = 400
CHAT_TIMEOUT_SECONDS = 45  # stop waiting for the model after this long (Scenario 5.3)
TEST_TIMEOUT_SECONDS = 1  # used only by the failure-test option below
WRONG_ENDPOINT = "fizzco-no-such-endpoint"  # used only by the failure-test option below

st.set_page_config(page_title="Fizzco Migration Assurance Hub", layout="wide")


def setting(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is not set; check app.yaml and the app resources")
    return value


@st.cache_resource
def workspace_client():
    return WorkspaceClient()  # credentials injected by the platform for the app's service principal


@st.cache_data(ttl=300, show_spinner="Querying the SQL warehouse...")
def load_recon_status():
    warehouse_id = setting("DATABRICKS_WAREHOUSE_ID")
    cfg = Config()
    LOGGER.info("recon: start, warehouse %s", warehouse_id)
    with sql.connect(server_hostname=cfg.host, http_path=f"/sql/1.0/warehouses/{warehouse_id}",
                     credentials_provider=lambda: cfg.authenticate) as conn:
        with conn.cursor() as cur:
            cur.execute(RECON_QUERY)
            df = cur.fetchall_arrow().to_pandas()
    LOGGER.info("recon: fetched %d rows", len(df))
    return df


def user_token():
    """The signed-in user's token, forwarded by the platform when user authorization is enabled; never shown or logged."""
    try:
        return st.context.headers.get("x-forwarded-access-token")
    except Exception:  # headers are not available outside a served app
        return None


def error_chain(exc):
    """Class and message of an error and of what caused it (the connector hides the real reason one level down)."""
    parts, seen = [], set()
    while exc is not None and id(exc) not in seen and len(parts) < 6:
        seen.add(id(exc))
        parts.append(f"{type(exc).__name__}: {H.short(exc, 400)}")
        context = getattr(exc, "context", None)  # the SQL connector keeps http-code and server message here
        if context:
            parts.append("context " + H.short(json.dumps(context, default=str), 600))
        exc = exc.__cause__ or exc.__context__
    return " <- ".join(parts)


def run_region_query(as_user):
    """Run the same query either as the signed-in user (their Unity Catalog permissions apply) or as the app."""
    warehouse_id = setting("DATABRICKS_WAREHOUSE_ID")
    cfg = Config()
    http_path = f"/sql/1.0/warehouses/{warehouse_id}"
    if as_user:
        token = user_token()
        if not token:
            return None
        connection = sql.connect(server_hostname=cfg.host, http_path=http_path, access_token=token)
    else:
        connection = sql.connect(server_hostname=cfg.host, http_path=http_path, credentials_provider=lambda: cfg.authenticate)
    with connection as conn:
        with conn.cursor() as cur:
            cur.execute(REGION_QUERY)
            df = cur.fetchall_arrow().to_pandas()
    LOGGER.info("access: %s query returned %d rows", "user" if as_user else "app", len(df))
    return df


def ask_genie(question):
    w = workspace_client()
    space_id = setting("GENIE_SPACE_ID")
    LOGGER.info("genie: start question (%d characters)", len(question))
    message = w.genie.start_conversation_and_wait(space_id=space_id, content=question, timeout=GENIE_TIMEOUT)
    parts = H.genie_parts(message)
    results = []
    for query in parts["queries"]:
        response = w.genie.get_message_attachment_query_result(
            space_id=space_id, conversation_id=message.conversation_id,
            message_id=message.message_id, attachment_id=query["attachment_id"])
        results.append(H.statement_rows(response))
    LOGGER.info("genie: done, %d text, %d queries", len(parts["texts"]), len(parts["queries"]))
    return parts, results


def retrieve_passages(question):
    w = workspace_client()
    index_name = setting("VECTOR_INDEX_NAME")
    LOGGER.info("rag: retrieve, question %d characters, top_k %d", len(question), TOP_K)
    found = w.vector_search_indexes.query_index(index_name=index_name, columns=H.CHUNK_COLUMNS,
                                                query_text=question, num_results=TOP_K, query_type="ANN")
    columns = [c.name for c in found.manifest.columns]
    return H.rows_to_dicts(columns, found.result.data_array or [])


def generate_answer(question, chunks, endpoint, timeout_seconds):
    """Ask the chat model; stop waiting after timeout_seconds (the abandoned call finishes in the background)."""
    w = workspace_client()
    messages = [ChatMessage(role=ChatMessageRole(m["role"]), content=m["content"]) for m in H.build_messages(question, chunks)]
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        future = pool.submit(w.serving_endpoints.query, name=endpoint, messages=messages,
                             max_tokens=CHAT_MAX_TOKENS, temperature=0.0)
        reply = future.result(timeout=timeout_seconds)  # raises TimeoutError when the limit passes
    finally:
        pool.shutdown(wait=False)
    return reply.choices[0].message.content.strip()


st.title("Fizzco Migration Assurance Hub")
st.caption("Synthetic data only. AI answers must be reviewed by a person before anyone acts on them.")
tab_recon, tab_data, tab_docs, tab_access = st.tabs(["Recon status", "Ask the data (Genie)", "Ask the runbooks (RAG)", "Access check"])

with tab_recon:
    try:
        recon = load_recon_status()
        status_choice = st.radio("Status", H.status_options(recon), horizontal=True)
        shown = H.filter_recon(recon, status_choice)
        st.caption(f"Showing {len(shown)} of {len(recon)} rows")
        st.dataframe(shown, use_container_width=True)
    except (sql.Error, RuntimeError, ValueError, KeyError) as exc:  # KeyError: a column is missing from the table
        LOGGER.error("recon failed: %s", exc)
        st.error(f"Could not load recon status: {exc}")

with tab_data:
    st.write("Ask a business question about sell-in, sell-out and promotions. Genie writes the SQL and runs it on the warehouse.")
    with st.form("genie_form"):
        genie_question = st.text_input("Question", value="What were net sell-in sales by region?")
        genie_go = st.form_submit_button("Ask Genie")
    if genie_go and genie_question.strip():
        try:
            with st.spinner("Genie is working (usually 20 to 40 seconds)..."):
                parts, results = ask_genie(genie_question.strip())
            for text in parts["texts"]:
                st.markdown(text)
            for query, result in zip(parts["queries"], results):
                st.caption(query["description"] or "Generated SQL")
                st.code(query["sql"], language="sql")
                if result["columns"]:
                    st.dataframe([dict(zip(result["columns"], row)) for row in result["rows"]], use_container_width=True)
            if not parts["texts"] and not parts["queries"]:
                st.warning("Genie returned no answer for this question.")
        except (DatabricksError, TimeoutError, RuntimeError, ValueError, AttributeError) as exc:
            LOGGER.error("genie failed: %s", exc)
            st.error(f"Genie could not answer: {exc}")

with tab_docs:
    st.write(f"Ask about a failed job or a rule. The answer comes only from the runbook documents (top {TOP_K} passages).")
    with st.expander("Test the failure handling (demo option)"):
        test_mode = st.radio("Model call", ["Normal", "Wrong endpoint name", f"{TEST_TIMEOUT_SECONDS}-second time limit"], index=0,
                             help="Simulates a missing endpoint or a slow one, so the error message can be checked. Leave on Normal for real use.")
    with st.form("rag_form"):
        rag_question = st.text_input("Question", value="Why did the sell_in reconciliation fail on 31 March 2026, and how was it fixed?")
        rag_go = st.form_submit_button("Ask the runbooks")
    if rag_go and rag_question.strip():
        question = rag_question.strip()
        chunks = []
        try:
            with st.spinner("Searching the runbooks..."):
                chunks = retrieve_passages(question)
        except Exception as exc:  # any failure here is shown as a friendly message, never a traceback
            info = H.classify_error(exc)
            LOGGER.error("rag retrieve failed: %s (%s)", info["error_class"], info["kind"])
            st.error("The runbook search is not available right now. Ask again in a few minutes, or tell the app owner.")
            with st.expander("Technical details"):
                st.code(f"{info['error_class']}: {H.short(exc) or '(no message)'}")
        else:
            endpoint = WRONG_ENDPOINT if test_mode.startswith("Wrong") else setting("CHAT_ENDPOINT")
            timeout_seconds = TEST_TIMEOUT_SECONDS if "time limit" in test_mode else CHAT_TIMEOUT_SECONDS
            try:
                with st.spinner(f"Writing the answer (waits up to {timeout_seconds} seconds)..."):
                    answer = generate_answer(question, chunks, endpoint, timeout_seconds)
                check = H.citation_check(answer, len(chunks))
                st.markdown(answer)
                if check["refused"]:
                    st.info("The documents do not contain an answer to this question.")
                elif not check["has_citation"]:
                    st.warning("The answer has no source labels; do not rely on it without checking.")
                elif not check["all_valid"]:
                    st.warning("The answer cites a source that does not exist; do not rely on it.")
                with st.expander("Sources used"):
                    for i, c in enumerate(chunks, 1):
                        st.markdown(f"**[S{i}]** `{c['chunk_id']}` ({c['feed']}, {c['doc_type']}): {c['section']}")
            except Exception as exc:  # timeout, missing endpoint, permission, busy service, anything else
                info = H.classify_error(exc)
                LOGGER.error("rag generate failed: %s (%s), test mode %s", info["error_class"], info["kind"], test_mode)
                st.warning(f"**{info['title']}.** {info['advice']}")
                with st.expander("Technical details"):
                    st.code(f"{info['error_class']}: {H.short(exc) or '(no message)'}")
                    if test_mode != "Normal":
                        st.caption(f"Failure test option in use: {test_mode}")
                st.markdown("**The passages found for your question (no AI summary):**")
                for i, c in enumerate(chunks[:3], 1):
                    with st.expander(f"[S{i}] {c['chunk_id']} - {c['section']}", expanded=(i == 1)):
                        st.text(H.short(c.get("text", ""), 700))  # st.text: the passage may start with a markdown heading mark

with tab_access:
    st.write("The same query, run two ways. The app contains no region logic: what each user sees is decided by the Unity Catalog row filter (Scenario 2.3).")
    if st.button("Show my view"):
        # Each view runs on its own, so one failure never hides the other and the message says which one failed.
        views = {}
        with st.spinner("Running the query as you and as the app..."):
            for key, as_user in (("user", True), ("app", False)):
                try:
                    views[key] = ("ok", run_region_query(as_user=as_user))
                except (sql.Error, RuntimeError, ValueError) as exc:
                    detail = error_chain(exc)
                    LOGGER.error("access check (%s view) failed: %s", key, detail)
                    views[key] = ("error", detail)
        st.subheader("As you (your permissions)")
        state, value = views["user"]
        if state == "error":
            st.error("Could not run the query with your own permissions.")
            st.text(value)
        elif value is None:
            st.info("User authorization is not enabled for this app, so your own permissions cannot be used. Ask the app owner to add the `sql` scope.")
        elif value.empty:
            st.warning("You can see no rows in this table.")
        else:
            st.caption(f"Signed in as {value['signed_in_as'].iloc[0]}")
            st.dataframe(value.drop(columns=["signed_in_as"]), use_container_width=True)
        st.subheader("As the app (its service principal)")
        state, value = views["app"]
        if state == "error":
            st.error("Could not run the query as the app.")
            st.text(value)
        elif value is None or value.empty:
            st.warning("The app's own identity sees no rows in this table.")
        else:
            st.dataframe(value.drop(columns=["signed_in_as"]), use_container_width=True)
