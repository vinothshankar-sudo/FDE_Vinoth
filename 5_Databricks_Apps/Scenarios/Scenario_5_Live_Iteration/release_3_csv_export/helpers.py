"""Pure helper functions for the Fizzco Hub tabs (no network calls, so they can be tested offline)."""
import re
from typing import Any, Dict, List, Sequence

NOT_FOUND_TEXT = "I could not find this in the Fizzco documents."

# Same grounded prompt as the Module 3 RAG pipeline (shared/rag/rag_lib.py).
GROUNDED_SYSTEM_PROMPT = (
    "You are a support assistant for Fizzco data engineering. Answer ONLY from the numbered context passages.\n"
    "Rules:\n"
    "1. Cite every fact with the passage label in square brackets, for example [S2]. Use only labels that exist.\n"
    f"2. If the passages do not contain the answer, reply exactly: {NOT_FOUND_TEXT} Do not guess, do not use general knowledge, and do not invent names, numbers or contacts.\n"
    "3. Be brief: at most five sentences or steps."
)

CHUNK_COLUMNS = ["chunk_id", "doc_id", "feed", "doc_type", "section", "text"]


def rows_to_dicts(columns: Sequence[str], rows: Sequence[Sequence[Any]]) -> List[Dict[str, Any]]:
    """Turn the data_array of a Vector Search response into dicts, in rank order."""
    return [dict(zip(columns, row)) for row in rows]


def format_context(chunks: Sequence[Dict[str, Any]]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(f"[S{i}] (source: {c.get('chunk_id')}; {c.get('doc_id')}; section: {c.get('section')})\n{c.get('text', '')}")
    return "\n\n".join(parts)


def build_messages(question: str, chunks: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    user = f"Context passages:\n\n{format_context(chunks)}\n\nQuestion: {question}"
    return [{"role": "system", "content": GROUNDED_SYSTEM_PROMPT}, {"role": "user", "content": user}]


def cited_labels(answer: str) -> List[str]:
    return sorted(set(re.findall(r"\[(S\d+)\]", answer)), key=lambda s: int(s[1:]))


def citation_check(answer: str, n_chunks: int) -> Dict[str, Any]:
    labels = cited_labels(answer)
    valid = [lab for lab in labels if 1 <= int(lab[1:]) <= n_chunks]
    return {"labels": labels, "all_valid": len(labels) == len(valid), "has_citation": bool(labels),
            "refused": NOT_FOUND_TEXT.lower()[:30] in answer.lower()}


def genie_parts(message: Any) -> Dict[str, Any]:
    """Pull the text answers and generated SQL out of a Genie message (SDK object)."""
    texts: List[str] = []
    queries: List[Dict[str, Any]] = []
    for att in getattr(message, "attachments", None) or []:
        text = getattr(att, "text", None)
        if text is not None and getattr(text, "content", None):
            texts.append(text.content)
        query = getattr(att, "query", None)
        if query is not None and getattr(query, "query", None):
            # Newer SDK versions call the id `attachment_id`; older ones call it `id`.
            attachment_id = getattr(att, "attachment_id", None) or getattr(att, "id", None) or getattr(query, "id", None)
            queries.append({"attachment_id": attachment_id, "sql": query.query,
                            "description": getattr(query, "description", None)})
    return {"texts": texts, "queries": queries}


def statement_rows(response: Any) -> Dict[str, Any]:
    """Columns and rows from a Genie query-result response (statement_response)."""
    stmt = getattr(response, "statement_response", None)
    if stmt is None or stmt.manifest is None or stmt.manifest.schema is None:
        return {"columns": [], "rows": []}
    columns = [c.name for c in (stmt.manifest.schema.columns or [])]
    rows = (stmt.result.data_array if stmt.result is not None else None) or []
    return {"columns": columns, "rows": rows}


# ---- Failure handling (Scenario 5.3) ---------------------------------------------------------
# Exception class name -> (kind, title, advice). The class is looked up along the exception's parent classes.
KIND_BY_CLASS = {
    "NotFound": "not_found", "ResourceDoesNotExist": "not_found",
    "PermissionDenied": "permission", "Unauthenticated": "permission",
    "TooManyRequests": "busy", "ResourceExhausted": "busy",
    "TemporarilyUnavailable": "unavailable", "InternalError": "unavailable",
    "DeadlineExceeded": "timeout", "TimeoutError": "timeout",
    "BadRequest": "bad_request", "InvalidParameterValue": "bad_request",
}
FRIENDLY = {
    "not_found": ("The AI model service could not be found",
                  "The endpoint name in the app configuration may be wrong, or the endpoint was removed. Tell the app owner."),
    "permission": ("The app is not allowed to use the AI model service",
                   "The app's permission on the endpoint is missing or was removed. Tell the app owner."),
    "busy": ("The AI model service is busy",
             "Too many requests were sent in a short time. Wait a minute and ask again."),
    "unavailable": ("The AI model service is temporarily unavailable",
                    "This is usually short. Ask again in a few minutes."),
    "timeout": ("The AI model service took too long to answer",
                "The request was stopped after the time limit. Ask again, or use the passages below."),
    "bad_request": ("The AI model service did not accept the request",
                    "The question or the passages may be too long. Try a shorter question."),
    "unknown": ("Something went wrong while asking the AI model service",
                "Ask again. If it keeps happening, tell the app owner and mention the time of the problem."),
}


def classify_error(exc: BaseException) -> Dict[str, str]:
    """Map any exception to a friendly kind, title and advice (no stack trace, no raw message)."""
    kind = "unknown"
    for cls in type(exc).__mro__:
        if cls.__name__ in KIND_BY_CLASS:
            kind = KIND_BY_CLASS[cls.__name__]
            break
    title, advice = FRIENDLY[kind]
    return {"kind": kind, "title": title, "advice": advice, "error_class": type(exc).__name__}


def short(text: str, limit: int = 300) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


# ---- Scenario 5.5, release 1: filter the recon table by status ----
ALL_STATUSES = "All"


def status_options(df):
    """'All' plus the statuses actually present in the data, so nothing is hard-coded."""
    return [ALL_STATUSES] + sorted(str(s) for s in df["status"].dropna().unique())


def filter_recon(df, status):
    """Rows of the recon table with the chosen status; 'All' returns every row."""
    if status == ALL_STATUSES:
        return df
    return df[df["status"] == status]


# ---- Scenario 5.5, release 2: chart of differing rows ----
def diff_chart_frame(df):
    """One column, diff_rows, indexed by recon_id and sorted by id: the table behind the bar chart."""
    return df.sort_values("recon_id").set_index("recon_id")[["diff_rows"]]


# ---- Scenario 5.5, release 3: CSV export of the rows shown ----
def to_csv_bytes(df):
    """The rows shown, as UTF-8 CSV with a header line and no row-number column."""
    return df.to_csv(index=False).encode("utf-8")


def export_filename(status):
    """recon_status_all.csv, recon_status_mismatch.csv, ... : the name says which rows are inside."""
    import re
    return "recon_status_" + re.sub(r"[^a-z0-9]+", "_", str(status).lower()).strip("_") + ".csv"
