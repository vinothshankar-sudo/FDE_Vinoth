"""Fizzco Migration Assurance Hub: tab 1 recon status, tab 2 ask the data (Genie), tab 3 ask the runbooks (RAG).

The app runs as its own service principal; Databricks supplies the credentials. Synthetic data only.
"""
import logging
import os
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

RECON_QUERY = (
    "SELECT recon_id, job_id, feed, recon_date, source_rows, trusted_rows, diff_rows, status "
    "FROM workspace.fizzco.gold_recon_results ORDER BY recon_date DESC, recon_id"
)
TOP_K = 5  # recommended in Scenario 4.5 (first relevant chunk was within rank 3 for 5 of 5 questions)
GENIE_TIMEOUT = timedelta(seconds=180)
CHAT_MAX_TOKENS = 400

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


def ask_runbooks(question):
    w = workspace_client()
    index_name, endpoint = setting("VECTOR_INDEX_NAME"), setting("CHAT_ENDPOINT")
    LOGGER.info("rag: start question (%d characters), top_k %d", len(question), TOP_K)
    found = w.vector_search_indexes.query_index(index_name=index_name, columns=H.CHUNK_COLUMNS,
                                                query_text=question, num_results=TOP_K, query_type="ANN")
    columns = [c.name for c in found.manifest.columns]
    chunks = H.rows_to_dicts(columns, found.result.data_array or [])
    messages = [ChatMessage(role=ChatMessageRole(m["role"]), content=m["content"]) for m in H.build_messages(question, chunks)]
    reply = w.serving_endpoints.query(name=endpoint, messages=messages, max_tokens=CHAT_MAX_TOKENS, temperature=0.0)
    answer = reply.choices[0].message.content.strip()
    LOGGER.info("rag: done, %d chunks, answer %d characters", len(chunks), len(answer))
    return answer, chunks


st.title("Fizzco Migration Assurance Hub")
st.caption("Synthetic data only. AI answers must be reviewed by a person before anyone acts on them.")
tab_recon, tab_data, tab_docs = st.tabs(["Recon status", "Ask the data (Genie)", "Ask the runbooks (RAG)"])

with tab_recon:
    try:
        st.dataframe(load_recon_status(), use_container_width=True)
    except (sql.Error, RuntimeError, ValueError) as exc:
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
    with st.form("rag_form"):
        rag_question = st.text_input("Question", value="Why did the sell_in reconciliation fail on 31 March 2026, and how was it fixed?")
        rag_go = st.form_submit_button("Ask the runbooks")
    if rag_go and rag_question.strip():
        try:
            with st.spinner("Searching the runbooks..."):
                answer, chunks = ask_runbooks(rag_question.strip())
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
        except (DatabricksError, TimeoutError, RuntimeError, ValueError, AttributeError) as exc:
            LOGGER.error("rag failed: %s", exc)
            st.error(f"Could not answer from the runbooks: {exc}")
