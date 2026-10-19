"""Scenario 4.2: freshness test. Insert one row after the index is built and time how long until it can be retrieved.

Run from the repo (folder: Scenario_2_Freshness_Test):
  python3 run_freshness.py | tee freshness_output.txt            # insert, sync, time it
  python3 run_freshness.py cleanup | tee freshness_cleanup_output.txt   # delete the test row and sync again (restores 42 rows)
Needs DATABRICKS_HOST and DATABRICKS_TOKEN in the environment (never in files).

The index is TRIGGERED, so a sync is requested explicitly (one call). Timing uses the status endpoint, which makes no
model calls; the similarity query runs only when the row count says the new row is in.
The test row is synthetic and marked TEST ONLY; run the cleanup step before Module 5 so the agent never retrieves it.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "vector"))
import vs_lib as V  # noqa: E402

SQL_FILE = Path(__file__).resolve().parent / "02_insert_new_runbook.sql"
NEW_ID = "RB-TEST-FRESHNESS-001#c1"
QUESTION = "By what time should the sell_out scan file arrive, and when do I raise an incident if it is late?"
MARKER = "06:30 UTC"
MAX_WAIT_MINUTES = 25


def found(hits) -> bool:
    return any(h["chunk_id"] == NEW_ID for h in hits) and any(MARKER in h.get("text", "") for h in hits)


def count_rows(client) -> int:
    return int(client.sql(f"SELECT COUNT(*) FROM {V.TABLE}")[0][0])


def wait_rows(client, rows: int, t_ref: float) -> float:
    last = None
    while True:
        info = client.index_get()
        status = (info or {}).get("status", {})
        msg = (status.get("ready"), status.get("indexed_row_count"), status.get("message"))
        if msg != last:
            V.out(f"  [{V.stamp()}] +{int(time.monotonic() - t_ref)} s  ready={msg[0]} rows={msg[1]} message={msg[2]}")
            last = msg
        if V.index_ready(info) and V.indexed_rows(info) == rows:
            return time.monotonic()
        if time.monotonic() - t_ref > MAX_WAIT_MINUTES * 60:
            raise RuntimeError(f"Index did not reach {rows} rows within {MAX_WAIT_MINUTES} minutes")
        time.sleep(10)


def insert_test() -> int:
    client = V.VSClient()
    insert, _delete = client.sql_statements(SQL_FILE)
    V.out(f"Freshness test, started {V.stamp()} UTC")
    if count_rows(client) != V.EXPECTED_ROWS:
        raise RuntimeError("Source table is not at 42 rows. Run the cleanup step first.")
    info = client.index_get()
    if not (V.index_ready(info) and V.indexed_rows(info) == V.EXPECTED_ROWS):
        raise RuntimeError("Index is not ready with 42 rows. Finish Scenario 4.1 first.")
    V.out(f"\nBefore the insert: query = {QUESTION}")
    before = client.query(QUESTION, 3)
    V.show_hits(before)
    V.out(f"New row retrievable before insert: {found(before)}")
    t_insert = time.monotonic()
    client.sql(insert)
    t_inserted = time.monotonic()
    V.out(f"\n[{V.stamp()}] Row {NEW_ID} inserted into {V.TABLE}; table now has {count_rows(client)} rows (SQL took {t_inserted - t_insert:.0f} s)")
    info = client.index_get()
    V.out(f"[{V.stamp()}] Index right after insert, before any sync: rows={V.indexed_rows(info)} (triggered index does not update by itself)")
    t_sync = time.monotonic()
    client.sync()
    V.out(f"[{V.stamp()}] Sync requested. Waiting for the index to reach 43 rows (status checks every 10 s, no model calls)")
    t_rows = wait_rows(client, V.EXPECTED_ROWS + 1, t_sync)
    hits = client.query(QUESTION, 3)
    t_query = time.monotonic()
    while not found(hits) and time.monotonic() - t_sync < MAX_WAIT_MINUTES * 60:
        time.sleep(30)
        hits = client.query(QUESTION, 3)
        t_query = time.monotonic()
    V.out(f"\nAfter the sync: query = {QUESTION}")
    V.show_hits(hits)
    ok = found(hits)
    V.out(f"New row retrievable after sync: {ok}")
    V.out("\nTiming (seconds since the sync request unless stated)")
    V.out("| event | time |")
    V.out("|---|---|")
    V.out(f"| INSERT statement duration | {t_inserted - t_insert:.0f} s |")
    V.out(f"| sync request to index row count = 43 | {V.fmt_seconds(t_rows - t_sync)} |")
    V.out(f"| sync request to row retrievable by similarity search | {V.fmt_seconds(t_query - t_sync)} |")
    V.out(f"| insert finished to row retrievable | {V.fmt_seconds(t_query - t_inserted)} |")
    V.out(f"\nHTTP calls made by this run: {client.calls}")
    return 0 if ok else 1


def cleanup() -> int:
    client = V.VSClient()
    _insert, delete = client.sql_statements(SQL_FILE)
    V.out(f"Cleanup, started {V.stamp()} UTC: delete the test row and sync again")
    client.sql(delete)
    V.out(f"[{V.stamp()}] Row deleted; table has {count_rows(client)} rows")
    t_sync = time.monotonic()
    client.sync()
    t_rows = wait_rows(client, V.EXPECTED_ROWS, t_sync)
    V.out(f"[{V.stamp()}] Index back to {V.EXPECTED_ROWS} rows, {V.fmt_seconds(t_rows - t_sync)} after the sync request (delete propagation time)")
    hits = client.query(QUESTION, 3)
    V.show_hits(hits)
    V.out(f"Test row still retrievable: {found(hits)}")
    V.out(f"HTTP calls made by this run: {client.calls}")
    return 0 if not found(hits) else 1


if __name__ == "__main__":
    V.R.setup_logging()
    sys.exit(cleanup() if len(sys.argv) > 1 and sys.argv[1] == "cleanup" else insert_test())
