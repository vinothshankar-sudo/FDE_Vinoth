"""Fizzco Migration Assurance agent (Module 6). Synthetic data only.

One tool-calling agent with three tools:
  get_recon_status  Unity Catalog function over workspace.fizzco.gold_recon_results   (Scenario 6.1)
  search_runbooks   Vector Search index of the runbook, policy and incident chunks    (Scenario 6.2)
  ask_genie         The Genie space "Retail Sales & Promotions Analytics"             (Scenario 6.2)

The model decides which tool to call. Every agent run, tool call and model call is traced with MLflow.
No credentials are in this file: inside a Databricks notebook the workspace supplies them.
"""
import json
import re

import mlflow
from mlflow.entities import SpanType

CFG = {
    "model_endpoint": "databricks-meta-llama-3-3-70b-instruct",   # must support tool calling; change here if it does not
    "function_name": "workspace.fizzco.get_recon_status",
    "index_name": "workspace.fizzco.runbook_chunks_index",
    "genie_space_id": "",          # set in the notebook: fa.CFG["genie_space_id"] = "..."
    "top_k": 5,                    # recommended in Scenario 4.5
    "max_rounds": 6,               # model calls per question before the agent gives up
    "max_tokens": 700,
    "genie_timeout_seconds": 180,
}
CHUNK_COLUMNS = ["chunk_id", "doc_id", "feed", "doc_type", "section", "text"]
MAX_TOOL_TEXT = 6000               # characters of one tool result sent back to the model

PROMPT_HEAD = "You are the Fizzco Migration Assurance assistant. Fizzco is a fictional company and all data is synthetic.\n"
TOOL_LINES = {
    "get_recon_status": "- get_recon_status(feed, recon_date): the reconciliation runs of one feed on one cut-off date. "
                        "feed is sell_in, sell_out, inventory or promo; recon_date is YYYY-MM-DD.\n",
    "search_runbooks": "- search_runbooks(query): runbooks, the reconciliation policy and incident notes: what a failure means and what to do.\n",
    "ask_genie": "- ask_genie(question): business numbers such as sales by region or promotion results.\n",
}
PROMPT_RULES = (
    "Rules:\n"
    "1. Use a tool when the answer depends on Fizzco data or documents. Answer directly, without a tool, for greetings and "
    "for general questions that need no Fizzco data.\n"
    "2. Never invent job ids, reconciliation ids, row counts, dates or steps. Use only values returned by tools.\n"
    "3. If a tool returns nothing or an error, say so plainly. Do not guess.\n"
    "4. When you use runbook, policy or incident text, cite the chunk id in square brackets, for example [RB-SELL-IN-001#c2]. "
    "Cite only chunk ids that search_runbooks returned in this conversation. Never cite a chunk you have not retrieved.\n"
    "5. If a feed has more than one run on the same date, report all of them in order: a rerun follows a failure.\n"
    "6. A date without a year means 2026.\n"
    "7. Recommend actions only if they come from the runbooks or the policy. Never recommend deleting or adding rows to make counts agree.\n"
    "8. Be brief: at most six sentences or steps.\n"
    "9. If asked why a run failed or what to do about a failed run, call BOTH tools, in this order: first get_recon_status for that "
    "feed and date to see what actually happened, including any rerun; then search_runbooks for the cause and the fix. Call "
    "search_runbooks even when the status is MATCH, because the cause and the fix must come from the runbooks. Base the advice on "
    "the current status: if a rerun already shows MATCH, say the issue is already resolved and state the cause and fix from the runbook."
)


def system_prompt(names=None):
    """The system prompt lists only the tools that are offered in this run."""
    names = list(TOOL_LINES) if names is None else list(names)
    tools = ("Tools:\n" + "".join(TOOL_LINES[n] for n in names)) if names else "You have no tools in this run.\n"
    return PROMPT_HEAD + tools + PROMPT_RULES


SYSTEM_PROMPT = system_prompt()

TOOL_SPECS = {
    "get_recon_status": {
        "type": "function",
        "function": {
            "name": "get_recon_status",
            "description": "Look up the reconciliation runs (run id, job id, row counts, difference, status, note) of one feed "
                           "on one cut-off date. A rerun after a failure appears as a second run.",
            "parameters": {"type": "object", "properties": {
                "feed": {"type": "string", "enum": ["sell_in", "sell_out", "inventory", "promo"],
                         "description": "The data feed."},
                "recon_date": {"type": "string", "description": "Cut-off date, YYYY-MM-DD, for example 2026-03-31."}},
                "required": ["feed", "recon_date"]}}},
    "search_runbooks": {
        "type": "function",
        "function": {
            "name": "search_runbooks",
            "description": "Search the Fizzco runbooks, reconciliation policy, incident notes and handbook. Use for what a "
                           "failure means, its cause and what to do about it. Returns numbered passages with chunk ids.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string", "description": "What to look for, in plain words."}},
                "required": ["query"]}}},
    "ask_genie": {
        "type": "function",
        "function": {
            "name": "ask_genie",
            "description": "Ask a business question about sell-in, sell-out, inventory or promotion numbers. "
                           "Genie writes and runs the SQL and returns the text, the SQL and the rows.",
            "parameters": {"type": "object", "properties": {
                "question": {"type": "string", "description": "The business question in plain English."}},
                "required": ["question"]}}},
}

_CACHE = {}


def _workspace():
    if "w" not in _CACHE:
        from databricks.sdk import WorkspaceClient
        _CACHE["w"] = WorkspaceClient()
    return _CACHE["w"]


def _uc_client():
    if "uc" not in _CACHE:
        from unitycatalog.ai.core.databricks import DatabricksFunctionClient
        _CACHE["uc"] = DatabricksFunctionClient()
    return _CACHE["uc"]


def _llm_client():
    if "llm" not in _CACHE:
        from databricks_openai import DatabricksOpenAI
        _CACHE["llm"] = DatabricksOpenAI()
    return _CACHE["llm"]


def enable_tracing(experiment=None):
    """Turn on MLflow tracing of the model calls (tool calls and the agent are traced by decorators)."""
    if experiment:
        mlflow.set_experiment(experiment)
    mlflow.openai.autolog()


# ---- tools -------------------------------------------------------------------------------------------
@mlflow.trace(name="get_recon_status", span_type=SpanType.TOOL)
def get_recon_status(feed, recon_date):
    result = _uc_client().execute_function(CFG["function_name"], {"feed": feed, "recon_date": recon_date})
    if getattr(result, "error", None):
        raise RuntimeError(f"UC function {CFG['function_name']} failed: {result.error}")
    return str(result.value)


@mlflow.trace(name="search_runbooks", span_type=SpanType.RETRIEVER)
def search_runbooks(query):
    found = _workspace().vector_search_indexes.query_index(
        index_name=CFG["index_name"], columns=CHUNK_COLUMNS, query_text=query,
        num_results=CFG["top_k"], query_type="ANN")
    columns = [c.name for c in found.manifest.columns]
    rows = [dict(zip(columns, r)) for r in (found.result.data_array or [])]
    return format_passages(rows)


@mlflow.trace(name="ask_genie", span_type=SpanType.TOOL)
def ask_genie(question):
    from datetime import timedelta
    if not CFG["genie_space_id"]:
        raise RuntimeError('CFG["genie_space_id"] is not set')
    w, space = _workspace(), CFG["genie_space_id"]
    message = w.genie.start_conversation_and_wait(
        space_id=space, content=question, timeout=timedelta(seconds=CFG["genie_timeout_seconds"]))
    texts, queries = [], []
    for att in getattr(message, "attachments", None) or []:
        text = getattr(att, "text", None)
        if text is not None and getattr(text, "content", None):
            texts.append(text.content)
        query = getattr(att, "query", None)
        if query is not None and getattr(query, "query", None):
            attachment_id = getattr(att, "attachment_id", None) or getattr(att, "id", None) or getattr(query, "id", None)
            queries.append((attachment_id, query.query))
    parts = list(texts)
    for attachment_id, sql_text in queries:
        parts.append("SQL: " + sql_text)
        response = w.genie.get_message_attachment_query_result(
            space_id=space, conversation_id=message.conversation_id,
            message_id=message.message_id, attachment_id=attachment_id)
        stmt = getattr(response, "statement_response", None)
        if stmt is not None and stmt.manifest is not None and stmt.manifest.schema is not None:
            cols = [c.name for c in (stmt.manifest.schema.columns or [])]
            rows = (stmt.result.data_array if stmt.result is not None else None) or []
            parts.append("COLUMNS: " + ", ".join(cols))
            parts.extend("ROW: " + ", ".join(str(v) for v in row) for row in rows[:25])
    return "\n".join(parts) if parts else "Genie returned no answer."


TOOL_FUNCTIONS = {"get_recon_status": get_recon_status, "search_runbooks": search_runbooks, "ask_genie": ask_genie}


def format_passages(rows):
    if not rows:
        return "No passages found."
    return "\n\n".join(f"[{r.get('chunk_id')}] ({r.get('doc_id')}; section: {r.get('section')})\n{r.get('text', '')}" for r in rows)


def run_tool(name, arguments_json):
    """Run one tool call and return (text for the model, ok). Errors become text so the model can say what failed."""
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return f"TOOL_ERROR: there is no tool called {name}", False
    try:
        args = json.loads(arguments_json or "{}")
        if not isinstance(args, dict):
            raise ValueError("arguments must be a JSON object")
        text = str(func(**args))
    except Exception as exc:  # noqa: BLE001 - any failure is reported to the model and recorded in the trace
        return f"TOOL_ERROR: {type(exc).__name__}: {str(exc)[:400]}", False
    return (text if len(text) <= MAX_TOOL_TEXT else text[:MAX_TOOL_TEXT] + "\n[truncated]"), True


# ---- the Unity Catalog function (one source of truth for 6.1 and the break/restore of 6.4) ----------
RECON_TABLE = "workspace.fizzco.gold_recon_results"


def recon_function_sql(table=RECON_TABLE):
    """CREATE OR REPLACE statement of the tool function; table is the table it reads."""
    return f"""CREATE OR REPLACE FUNCTION {CFG['function_name']}(
  feed STRING COMMENT 'Data feed to look up: sell_in, sell_out, inventory or promo',
  recon_date STRING COMMENT 'Reconciliation cut-off date in YYYY-MM-DD format, for example 2026-03-31'
)
RETURNS STRING
COMMENT 'Returns every reconciliation run (run id, job id, row counts, difference, status, note) for one feed on one cut-off date, in id order. A rerun after a failure appears as a second line. Returns a plain message when no run exists.'
RETURN (
  SELECT CASE
    WHEN COUNT(*) = 0 THEN concat('No reconciliation run found for feed ', get_recon_status.feed, ' on ', get_recon_status.recon_date)
    ELSE array_join(sort_array(collect_list(concat(
      r.recon_id, ' | job ', r.job_id, ' | feed ', r.feed, ' | date ', CAST(r.recon_date AS STRING),
      ' | source_rows ', CAST(r.source_rows AS STRING), ' | trusted_rows ', CAST(r.trusted_rows AS STRING),
      ' | diff_rows ', CAST(r.diff_rows AS STRING), ' | status ', r.status, ' | note ', COALESCE(r.note, '')))), '\\n')
  END
  FROM {table} r
  WHERE r.feed = get_recon_status.feed
    AND r.recon_date = try_cast(get_recon_status.recon_date AS DATE)
)"""


def find_genie_space(title_part="Retail Sales"):
    """(space_id, title) of the Genie space whose title contains title_part; raises if there is not exactly one."""
    spaces = [s for s in (_workspace().genie.list_spaces().spaces or []) if title_part.lower() in (s.title or "").lower()]
    if len(spaces) != 1:
        raise RuntimeError(f"expected one Genie space with '{title_part}' in its title, found {len(spaces)}: "
                           + ", ".join(f"{s.title} ({s.space_id})" for s in spaces))
    return spaces[0].space_id, spaces[0].title


# ---- reading a trace (Scenario 6.4) -------------------------------------------------------------------
def trace_summary(trace, width=160):
    """One row per span: order, name, type, status, milliseconds, input and output previews. Read it top to bottom."""
    rows = []
    for i, span in enumerate(sorted(trace.data.spans, key=lambda s: s.start_time_ns), 1):
        status = getattr(span.status, "status_code", span.status)
        rows.append({"step": i, "span": span.name, "type": str(span.span_type), "status": str(getattr(status, "value", status)),
                     "ms": round((span.end_time_ns - span.start_time_ns) / 1e6), "input": " ".join(str(span.inputs).split())[:width],
                     "output": " ".join(str(span.outputs).split())[:width]})
    return rows


# ---- the agent ---------------------------------------------------------------------------------------
@mlflow.trace(name="fizzco_agent", span_type=SpanType.AGENT)
def run_agent(question, enabled=None, client=None):
    """Answer one question. Returns {"answer", "tool_calls": [{"name", "arguments", "ok"}], "rounds"}.

    enabled: tool names the model may use (default: all three). client: an OpenAI-style client (tests pass a fake).
    """
    names = list(enabled) if enabled is not None else list(TOOL_SPECS)
    tools = [TOOL_SPECS[n] for n in names]
    client = client or _llm_client()
    messages = [{"role": "system", "content": system_prompt(names)}, {"role": "user", "content": question}]
    calls = []
    for round_no in range(1, CFG["max_rounds"] + 1):
        kwargs = dict(model=CFG["model_endpoint"], messages=messages, temperature=0, max_tokens=CFG["max_tokens"])
        if tools:
            kwargs.update(tools=tools, tool_choice="auto")
        message = client.chat.completions.create(**kwargs).choices[0].message
        tool_calls = getattr(message, "tool_calls", None) or []
        if not tool_calls:
            return {"answer": (message.content or "").strip(), "tool_calls": calls, "rounds": round_no}
        messages.append({"role": "assistant", "content": message.content or "", "tool_calls": [
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in tool_calls]})
        for tc in tool_calls:
            if tc.function.name not in names:
                text, ok = f"TOOL_ERROR: tool {tc.function.name} is not available", False
            else:
                text, ok = run_tool(tc.function.name, tc.function.arguments)
            calls.append({"name": tc.function.name, "arguments": tc.function.arguments, "ok": ok})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": text})
    return {"answer": "I could not finish: too many tool steps. Please ask a narrower question.",
            "tool_calls": calls, "rounds": CFG["max_rounds"]}


def ask(question, enabled=None):
    """Answer text only: the function the evaluation calls."""
    return run_agent(question, enabled=enabled)["answer"]


def tool_names(result):
    return [c["name"] for c in result["tool_calls"]]
