"""Scenario 4.4: index type comparison. Delta Sync (built in 4.1) vs Direct Vector Access.

Run from the repo (folder: Scenario_4_Index_Type_Comparison):
  python3 run_direct_access.py | tee direct_access_output.txt
  python3 run_direct_access.py delete      # only if a Direct Access index was created and you want it removed
Needs DATABRICKS_HOST and DATABRICKS_TOKEN in the environment (never in files).

Databricks Free Edition lists Direct Vector Access as unsupported. This script ATTEMPTS the creation once and records the
exact reply, so the README can quote what the workspace actually said. If the creation is accepted (the docs may be out of
date), it pushes the 42 chunk vectors from the Module 3 cache (no new embedding calls) and runs the same query, so both
index types can be compared with real numbers. Nothing is faked: whichever branch happens is what gets reported.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "vector"))
import vs_lib as V  # noqa: E402

QUESTION = "Why did the sell_in reconciliation fail on 31 March 2026, and how was it fixed?"
GOLD = ["The cause was an off-by-one error in the date filter", "The fix is to make the end date inclusive"]
SCHEMA = {"chunk_id": "string", "doc_id": "string", "feed": "string", "doc_type": "string", "section": "string",
          "text": "string", "embedding": "array<float>"}


def create_body() -> dict:
    return {"name": V.DIRECT_INDEX, "endpoint_name": V.ENDPOINT, "primary_key": "chunk_id", "index_type": "DIRECT_ACCESS",
            "direct_access_index_spec": {
                "embedding_vector_columns": [{"name": "embedding", "embedding_dimension": 1024}],
                "schema_json": json.dumps(SCHEMA)}}


def main() -> int:
    V.R.setup_logging()
    client = V.VSClient()
    V.out(f"Attempt to create a Direct Vector Access index: {V.DIRECT_INDEX} on endpoint {V.ENDPOINT}")
    t0 = time.monotonic()
    reply = client.request("POST", "/api/2.0/vector-search/indexes", create_body(),
                           allow=(400, 401, 402, 403, 404, 409, 412, 422, 429))
    V.out(f"[{V.stamp()}] Reply after {time.monotonic() - t0:.0f} s: {json.dumps(reply)[:600]}")
    if "_status" in reply:
        V.out("\nResult: the workspace did NOT create a Direct Vector Access index. See the reply above (quoted in the README).")
        V.out(f"HTTP calls made by this run: {client.calls}")
        return 0
    V.out("\nResult: creation accepted. Loading the 42 cached vectors and querying.")
    chunks = V.build_chunks()
    embedder = V.R.DatabricksEmbedder(client.base)
    vectors = embedder.embed([c.text for c in chunks])
    rows = [{"chunk_id": c.chunk_id, "doc_id": c.doc_id, "feed": c.feed, "doc_type": c.doc_type, "section": c.section,
             "text": c.text, "embedding": [float(x) for x in v]} for c, v in zip(chunks, vectors)]
    t1 = time.monotonic()
    client.request("POST", f"/api/2.0/vector-search/indexes/{V.DIRECT_INDEX}/upsert-data", {"inputs_json": json.dumps(rows)})
    V.out(f"[{V.stamp()}] Upsert of {len(rows)} rows took {time.monotonic() - t1:.0f} s")
    qvec = [float(x) for x in embedder.embed([QUESTION])[0]]
    body = {"query_vector": qvec, "columns": V.RESULT_COLUMNS, "num_results": 3}
    time.sleep(5)
    resp = client.request("POST", f"/api/2.0/vector-search/indexes/{V.DIRECT_INDEX}/query", body)
    names = [c["name"] for c in resp["manifest"]["columns"]]
    hits = [dict(zip(names, r), rank=i) for i, r in enumerate(resp["result"]["data_array"], 1)]
    V.show_hits(hits)
    V.out(f"Gold chunk in top 3: rank {V.gold_rank_dicts(hits, GOLD)}")
    V.out(f"HTTP calls made by this run: {client.calls}")
    return 0


def delete() -> int:
    client = V.VSClient()
    client.delete_index(V.DIRECT_INDEX)
    V.out(f"Deleted {V.DIRECT_INDEX}")
    return 0


TEST_ID = "RB-TEST-FRESHNESS-001#c1"
TEST_TEXT = ("Runbook: sell_out scan file arrives late. TEST ONLY document used to time Vector Search freshness; it is not a real "
             "Fizzco procedure. The retailer scan file for sell_out should arrive by 06:30 UTC. If it has not arrived, wait until "
             "08:00 UTC before raising an incident. After 08:00 UTC, ask the retailer owner to resend the scan file, then trigger "
             "the sell_out pipeline manually with the load_date set to the missing day.")
FRESH_QUESTION = "By what time should the sell_out scan file arrive, and when do I raise an incident if it is late?"


def query_vec(client, vec, k=3):
    body = {"query_vector": vec, "columns": V.RESULT_COLUMNS, "num_results": k}
    resp = client.request("POST", f"/api/2.0/vector-search/indexes/{V.DIRECT_INDEX}/query", body)
    names = [c["name"] for c in resp["manifest"]["columns"]]
    return [dict(zip(names, r), rank=i) for i, r in enumerate(resp["result"]["data_array"], 1)]


def delete_path(primary_key: str) -> str:
    from urllib.parse import quote
    return f"/api/2.0/vector-search/indexes/{V.DIRECT_INDEX}/delete-data?primary_keys={quote(primary_key, safe='')}"


def has_test_row(hits) -> bool:
    return any(h["chunk_id"] == TEST_ID for h in hits)


def poll(client, qvec, want_present: bool, limit_s: int = 180):
    start = time.monotonic()
    while time.monotonic() - start < limit_s:
        hits = query_vec(client, qvec)
        if has_test_row(hits) == want_present:
            return time.monotonic() - start, hits
        time.sleep(1)
    return None, []


def freshness() -> int:
    """Direct Access freshness: upsert one test row, time until a query returns it, then delete it and time that."""
    V.R.setup_logging()
    client = V.VSClient()
    info = client.index_get(V.DIRECT_INDEX)
    if not V.index_ready(info):
        V.out("Direct Access index is not ready yet; wait a minute and rerun.")
        return 1
    embedder = V.R.DatabricksEmbedder(client.base)
    row_vec = [float(x) for x in embedder.embed([TEST_TEXT])[0]]
    qvec = [float(x) for x in embedder.embed([FRESH_QUESTION])[0]]
    V.out(f"Direct Access freshness test, started {V.stamp()} UTC")
    before = query_vec(client, qvec)
    if has_test_row(before):
        V.out("Test row is left over from an earlier run; deleting it first so the timing starts clean.")
        client.request("DELETE", delete_path(TEST_ID))
        poll(client, qvec, False)
        before = query_vec(client, qvec)
    V.show_hits(before)
    V.out(f"Test row retrievable before the upsert: {has_test_row(before)}")
    row = {"chunk_id": TEST_ID, "doc_id": "RB-TEST-FRESHNESS-001", "feed": "sell_out", "doc_type": "runbook",
           "section": "Late scan file", "text": TEST_TEXT, "embedding": row_vec}
    t0 = time.monotonic()
    client.request("POST", f"/api/2.0/vector-search/indexes/{V.DIRECT_INDEX}/upsert-data", {"inputs_json": json.dumps([row])})
    t_upsert = time.monotonic() - t0
    V.out(f"[{V.stamp()}] Upserted 1 row in {t_upsert:.1f} s; polling a query every 1 s")
    found_s, hits = poll(client, qvec, True)
    V.show_hits(hits)
    V.out(f"Row retrievable {found_s if found_s is None else round(t_upsert + found_s, 1)} s after the upsert started (upsert call {t_upsert:.1f} s)")
    t1 = time.monotonic()
    client.request("DELETE", delete_path(TEST_ID))
    t_del = time.monotonic() - t1
    gone_s, hits2 = poll(client, qvec, False)
    V.show_hits(hits2)
    V.out(f"Row gone {gone_s if gone_s is None else round(t_del + gone_s, 1)} s after the delete started (delete call {t_del:.1f} s)")
    V.out("\nTiming (Direct Vector Access, 1 s query polling)")
    V.out("| event | seconds |")
    V.out("|---|---|")
    V.out(f"| upsert call | {t_upsert:.1f} |")
    V.out(f"| upsert start to retrievable | {'not found within 180 s' if found_s is None else round(t_upsert + found_s, 1)} |")
    V.out(f"| delete call | {t_del:.1f} |")
    V.out(f"| delete start to gone | {'still present after 180 s' if gone_s is None else round(t_del + gone_s, 1)} |")
    V.out(f"HTTP calls made by this run: {client.calls}; model-serving calls: {client.base.calls}")
    return 0 if found_s is not None and gone_s is not None else 1


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit(delete() if arg == "delete" else freshness() if arg == "freshness" else main())
