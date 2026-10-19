"""Shared helpers for the Module 4 scenarios: Databricks SQL, Vector Search REST, and the Fizzco chunk table.

Credentials come only from the environment (DATABRICKS_HOST, DATABRICKS_TOKEN). Nothing is stored in files.
The token is cleaned by the same code as Module 3 (rag_lib.DatabricksClient), which removes hidden terminal characters.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

VECTOR_DIR = Path(__file__).resolve().parent
ASSIGNMENT_DIR = VECTOR_DIR.parents[1]
sys.path.insert(0, str(ASSIGNMENT_DIR / "shared" / "rag"))
import rag_lib as R  # noqa: E402
import rag_setup as S  # noqa: E402

CATALOG, SCHEMA = "workspace", "fizzco"
TABLE = f"{CATALOG}.{SCHEMA}.runbook_chunks"
INDEX = f"{CATALOG}.{SCHEMA}.runbook_chunks_index"
DIRECT_INDEX = f"{CATALOG}.{SCHEMA}.runbook_chunks_direct_index"
ENDPOINT = "fizzco_vs"
EMBED_ENDPOINT = "databricks-gte-large-en"
CHUNK_SIZE, CHUNK_OVERLAP = 200, 40  # chosen in Scenario 3.2
EXPECTED_ROWS = 42
RESULT_COLUMNS = ["chunk_id", "doc_id", "feed", "doc_type", "section", "text"]
RETRY_STATUSES = {429, 500, 502, 503, 504}
PACE_SECONDS = 1.0


def now() -> datetime:
    return datetime.now(timezone.utc)


def stamp(dt: Optional[datetime] = None) -> str:
    return (dt or now()).strftime("%H:%M:%S")


def out(text: str = "") -> None:
    R.write_out(text)
    sys.stdout.flush()  # show progress live even when piped to tee


def fmt_seconds(seconds: float) -> str:
    seconds = int(round(seconds))
    return f"{seconds // 60} min {seconds % 60:02d} s ({seconds} s)"


class VSClient:
    """REST client for SQL statements and Vector Search. Pauses between calls and backs off on 429/5xx."""

    def __init__(self) -> None:
        self.base = R.DatabricksClient()
        import re
        from urllib.parse import urlparse
        parsed = urlparse(self.base.host.strip())
        if parsed.scheme == "https" and parsed.netloc:
            self.base.host = f"https://{parsed.netloc}"  # drop any path such as /compute or ?o=123
        host = self.base.host
        if host != "cache-only" and not re.fullmatch(r"https://[A-Za-z0-9.-]+\.(cloud\.databricks\.com|azuredatabricks\.net|gcp\.databricks\.com)", host):
            raise RuntimeError(
                "DATABRICKS_HOST must look like https://dbc-xxxxxxxx-xxxx.cloud.databricks.com (your own workspace address, "
                "copied from the browser address bar, no path after .com). Current value does not match that shape.")
        self.calls = 0
        self._last = 0.0
        self._warehouse: Optional[str] = None

    def request(self, method: str, path: str, body: Optional[dict] = None, allow: Sequence[int] = ()) -> Any:
        url = self.base.host + path
        delay = 4.0
        for attempt in range(1, 8):
            wait = self._last + PACE_SECONDS - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            try:
                resp = self.base._requests.request(method, url, headers=self.base._headers, json=body, timeout=90)
            except self.base._requests.exceptions.ConnectionError as exc:
                raise RuntimeError(
                    f"Cannot reach {self.base.host}. This is usually a wrong DATABRICKS_HOST: copy the start of the "
                    "address bar of your own workspace (https://...cloud.databricks.com), not an example.") from exc
            self._last = time.monotonic()
            self.calls += 1
            if resp.status_code in RETRY_STATUSES and attempt < 7:
                R.LOGGER.warning("%s %s returned %s, retry %d in %.0fs", method, path, resp.status_code, attempt, delay)
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            if resp.status_code in allow:
                return {"_status": resp.status_code, "_body": resp.text[:600]}
            if resp.status_code >= 400:
                raise RuntimeError(f"{method} {path} returned {resp.status_code}: {resp.text[:600]}")
            return resp.json() if resp.text.strip() else {}
        raise RuntimeError(f"{method} {path} failed after 7 attempts")

    # ----- SQL -----------------------------------------------------------------------------
    def warehouse_id(self) -> str:
        if self._warehouse is None:
            data = self.request("GET", "/api/2.0/sql/warehouses")
            warehouses = data.get("warehouses", [])
            if not warehouses:
                raise RuntimeError("No SQL warehouse found in this workspace.")
            self._warehouse = warehouses[0]["id"]
        return self._warehouse

    def sql(self, statement: str) -> List[List[Any]]:
        body = {"warehouse_id": self.warehouse_id(), "statement": statement, "wait_timeout": "30s",
                "on_wait_timeout": "CONTINUE"}
        resp = self.request("POST", "/api/2.0/sql/statements", body)
        statement_id = resp["statement_id"]
        deadline = time.monotonic() + 600
        while resp["status"]["state"] in ("PENDING", "RUNNING"):
            if time.monotonic() > deadline:
                raise RuntimeError("SQL statement did not finish in 10 minutes")
            time.sleep(5)
            resp = self.request("GET", f"/api/2.0/sql/statements/{statement_id}")
        if resp["status"]["state"] != "SUCCEEDED":
            raise RuntimeError(f"SQL failed: {resp['status'].get('error', resp['status'])}")
        return resp.get("result", {}).get("data_array", []) or []

    @staticmethod
    def sql_statements(path: Path) -> List[str]:
        """Split a file whose statements are separated by a line that contains only '-- STATEMENT'."""
        statements = []
        for part in path.read_text(encoding="utf-8").split("-- STATEMENT"):
            statement = "\n".join(l for l in part.strip().splitlines() if not l.startswith("-- ")).strip()
            if statement:
                statements.append(statement)
        return statements

    # ----- Vector Search -------------------------------------------------------------------
    def endpoint_state(self, name: str = ENDPOINT) -> Optional[str]:
        resp = self.request("GET", f"/api/2.0/vector-search/endpoints/{name}", allow=(404,))
        if resp.get("_status") == 404:
            return None
        return resp.get("endpoint_status", {}).get("state", "UNKNOWN")

    def create_endpoint(self, name: str = ENDPOINT) -> None:
        self.request("POST", "/api/2.0/vector-search/endpoints", {"name": name, "endpoint_type": "STANDARD"})

    def index_get(self, name: str = INDEX) -> Optional[dict]:
        resp = self.request("GET", f"/api/2.0/vector-search/indexes/{name}", allow=(404,))
        return None if resp.get("_status") == 404 else resp

    def create_delta_sync_index(self, name: str = INDEX, pipeline: str = "TRIGGERED") -> dict:
        body = {"name": name, "endpoint_name": ENDPOINT, "primary_key": "chunk_id", "index_type": "DELTA_SYNC",
                "delta_sync_index_spec": {
                    "source_table": TABLE, "pipeline_type": pipeline,
                    "embedding_source_columns": [{"name": "text", "embedding_model_endpoint_name": EMBED_ENDPOINT}]}}
        return self.request("POST", "/api/2.0/vector-search/indexes", body)

    def sync(self, name: str = INDEX) -> None:
        self.request("POST", f"/api/2.0/vector-search/indexes/{name}/sync")

    def delete_index(self, name: str) -> None:
        self.request("DELETE", f"/api/2.0/vector-search/indexes/{name}")

    def query(self, text: str, k: int, filters: Optional[Dict[str, List[str]]] = None,
              index: str = INDEX, columns: Sequence[str] = RESULT_COLUMNS) -> List[dict]:
        body: Dict[str, Any] = {"query_text": text, "columns": list(columns), "num_results": k, "query_type": "ANN"}
        if filters:
            body["filters_json"] = json.dumps(filters)
        resp = self.request("POST", f"/api/2.0/vector-search/indexes/{index}/query", body)
        names = [c["name"] for c in resp["manifest"]["columns"]]
        rows = resp.get("result", {}).get("data_array", []) or []
        hits = []
        for rank, row in enumerate(rows, 1):
            item = dict(zip(names, row))
            item["rank"] = rank
            hits.append(item)
        return hits


def index_ready(info: Optional[dict]) -> bool:
    return bool(info) and bool(info.get("status", {}).get("ready"))


def indexed_rows(info: Optional[dict]) -> Optional[int]:
    if not info:
        return None
    value = info.get("status", {}).get("indexed_row_count")
    return int(value) if value is not None else None


def wait_for_index(client: VSClient, rows: int, name: str = INDEX, max_minutes: int = 25, poll: int = 15) -> dict:
    """Poll the index status until it is ready and holds `rows` rows. Status polls use no model calls."""
    start = time.monotonic()
    last_message = None
    while True:
        info = client.index_get(name)
        status = (info or {}).get("status", {})
        message = status.get("message")
        if message != last_message:
            out(f"  [{stamp()}] index status: ready={status.get('ready')} rows={status.get('indexed_row_count')} message={message}")
            last_message = message
        if index_ready(info) and indexed_rows(info) == rows:
            return info
        if time.monotonic() - start > max_minutes * 60:
            raise RuntimeError(f"Index not ready with {rows} rows after {max_minutes} minutes; check the UI and rerun.")
        time.sleep(poll)


# ----- Fizzco chunk data -------------------------------------------------------------------
def build_chunks() -> List[R.Chunk]:
    chunks = R.chunk_corpus(S.load_docs(), CHUNK_SIZE, CHUNK_OVERLAP)
    if len(chunks) != EXPECTED_ROWS:
        raise RuntimeError(f"Expected {EXPECTED_ROWS} chunks (Scenario 3.2 setting), got {len(chunks)}")
    return chunks


def sql_text(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def chunk_row_sql(c: R.Chunk) -> str:
    return "(" + ", ".join([sql_text(c.chunk_id), sql_text(c.doc_id), sql_text(c.title), sql_text(c.feed),
                             sql_text(c.doc_type), sql_text(c.section), str(c.position), str(c.n_tokens),
                             sql_text(c.text)]) + ")"


def show_hits(hits: Sequence[dict], limit_text: int = 110) -> None:
    for h in hits:
        out(f"  {h['rank']}. {h['chunk_id']:<24} score={float(h.get('score', 0)):.4f} [{h.get('feed')}/{h.get('doc_type')}] {h.get('section')}")


def gold_rank_dicts(hits: Sequence[dict], phrases: Sequence[str]) -> Optional[int]:
    wanted = [R.normalise_text(p) for p in phrases]
    for h in hits:
        text = R.normalise_text(h.get("text", ""))
        if any(p in text for p in wanted):
            return h["rank"]
    return None


def hit_to_chunk_hit(h: dict) -> R.Hit:
    """Wrap a Vector Search row so rag_lib's prompt builder and chat can be reused."""
    chunk = R.Chunk(chunk_id=h["chunk_id"], doc_id=h.get("doc_id", ""), title=h.get("doc_id", ""),
                    doc_type=h.get("doc_type", ""), feed=h.get("feed", ""), section=h.get("section", ""),
                    text=h.get("text", ""), n_tokens=len(h.get("text", "").split()))
    return R.Hit(chunk, float(h.get("score", 0)), h["rank"], "vector_search", {})
