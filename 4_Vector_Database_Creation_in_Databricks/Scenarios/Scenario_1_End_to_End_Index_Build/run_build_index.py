"""Scenario 4.1: end-to-end index build. Delta table with CDF, Vector Search endpoint, Delta Sync index, one query.

Run from the repo:  python3 4_Vector_Database_Creation_in_Databricks/Scenarios/Scenario_1_End_to_End_Index_Build/run_build_index.py | tee build_index_output.txt
Needs DATABRICKS_HOST and DATABRICKS_TOKEN in the environment (never in files).

The script is safe to rerun: each step checks what already exists and skips it. It creates at most ONE endpoint and ONE index
(Free Edition allows one endpoint with one search unit). Embeddings are managed by Databricks (model databricks-gte-large-en).
Pipeline type is TRIGGERED, so the index only does work when a sync is requested.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "vector"))
import vs_lib as V  # noqa: E402

SQL_FILE = Path(__file__).resolve().parent / "01_create_runbook_chunks.sql"
QUESTION = "Why did the sell_in reconciliation fail on 31 March 2026, and how was it fixed?"
GOLD = ["The cause was an off-by-one error in the date filter", "The fix is to make the end date inclusive"]


def ensure_table(client: V.VSClient) -> None:
    ddl, insert = client.sql_statements(SQL_FILE)
    client.sql(ddl)
    count = int(client.sql(f"SELECT COUNT(*) FROM {V.TABLE}")[0][0])
    if count == 0:
        client.sql(insert)
        count = int(client.sql(f"SELECT COUNT(*) FROM {V.TABLE}")[0][0])
        V.out(f"[{V.stamp()}] Table {V.TABLE} created and loaded: {count} rows")
    else:
        V.out(f"[{V.stamp()}] Table {V.TABLE} already exists with {count} rows (not reloaded)")
    if count != V.EXPECTED_ROWS:
        raise RuntimeError(f"Expected {V.EXPECTED_ROWS} rows, found {count}. Stop and check before building the index.")
    props = client.sql(f"SHOW TBLPROPERTIES {V.TABLE} ('delta.enableChangeDataFeed')")
    V.out(f"  delta.enableChangeDataFeed = {props[0][-1] if props else 'unknown'}")
    feeds = client.sql(f"SELECT feed, COUNT(*) FROM {V.TABLE} GROUP BY feed ORDER BY feed")
    V.out("  rows per feed: " + ", ".join(f"{r[0]}={r[1]}" for r in feeds))


def ensure_endpoint(client: V.VSClient) -> None:
    state = client.endpoint_state()
    if state is None:
        client.create_endpoint()
        V.out(f"[{V.stamp()}] Endpoint {V.ENDPOINT} creation requested")
    start = time.monotonic()
    while True:
        state = client.endpoint_state()
        V.out(f"  [{V.stamp()}] endpoint state: {state}")
        if state == "ONLINE":
            return
        if time.monotonic() - start > 25 * 60:
            raise RuntimeError("Endpoint not ONLINE after 25 minutes; check Compute > Vector Search in the workspace.")
        time.sleep(30)


def ensure_index(client: V.VSClient) -> None:
    if client.index_get() is None:
        t0 = time.monotonic()
        client.create_delta_sync_index()
        V.out(f"[{V.stamp()}] Delta Sync index {V.INDEX} creation requested (TRIGGERED, managed embeddings)")
        V.wait_for_index(client, V.EXPECTED_ROWS)
        V.out(f"[{V.stamp()}] Index ready with {V.EXPECTED_ROWS} rows after {V.fmt_seconds(time.monotonic() - t0)}")
    else:
        info = V.wait_for_index(client, V.EXPECTED_ROWS)
        V.out(f"[{V.stamp()}] Index already existed and is ready with {V.indexed_rows(info)} rows")


def main() -> int:
    V.R.setup_logging()
    client = V.VSClient()
    V.out(f"Step 1: source table with Change Data Feed ({V.TABLE})")
    ensure_table(client)
    V.out(f"\nStep 2: Vector Search endpoint ({V.ENDPOINT})")
    ensure_endpoint(client)
    V.out(f"\nStep 3: Delta Sync index ({V.INDEX})")
    ensure_index(client)
    V.out("\nStep 4: basic similarity search, top_k = 3")
    V.out(f"Question: {QUESTION}")
    hits = client.query(QUESTION, 3)
    V.show_hits(hits)
    rank = V.gold_rank_dicts(hits, GOLD)
    V.out(f"Gold chunk (the one that holds the answer) in top 3: {rank is not None} (rank {rank})")
    if hits:
        V.out(f"Top hit text (first 200 characters): {V.S.excerpt(hits[0]['text'], 200)}")
    V.out(f"\nHTTP calls made by this run: {client.calls}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
