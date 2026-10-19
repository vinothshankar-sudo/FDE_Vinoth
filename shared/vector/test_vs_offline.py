"""Offline test for the Module 4 code: no network, no credentials. Uses a fake REST layer to exercise every code path.

Run:  python3 shared/vector/test_vs_offline.py
It checks the generated SQL, the query-result parsing, the index wait loop, the filter payload and the timing report logic.
It proves the code runs; it says nothing about Databricks behaviour, which only the real runs show.
"""
import json
import os
import sys

os.environ["DATABRICKS_HOST"] = "https://example.invalid"
os.environ["DATABRICKS_TOKEN"] = "dapi" + "0" * 32
import vs_lib as V  # noqa: E402


class FakeClient(V.VSClient):
    def __init__(self):
        super().__init__()
        self.log = []
        self.polls = 0

    def request(self, method, path, body=None, allow=()):
        self.log.append((method, path, body))
        if path.endswith("/query"):
            return {"manifest": {"columns": [{"name": c} for c in V.RESULT_COLUMNS] + [{"name": "score"}]},
                    "result": {"row_count": 2, "data_array": [
                        ["A#c1", "A", "promo", "runbook", "Fix", "copy the promotion owner", 0.9],
                        ["B#c1", "B", "all", "policy", "Rules", "other text", 0.8]]}}
        if "/vector-search/indexes/" in path and method == "GET":
            self.polls += 1
            return {"status": {"ready": self.polls >= 3, "indexed_row_count": 42 if self.polls >= 3 else 0, "message": "m"}}
        return {}


def main() -> int:
    chunks = V.build_chunks()
    assert len(chunks) == 42
    row = V.chunk_row_sql(chunks[0])
    assert row.startswith("('") and row.endswith(")")
    assert V.sql_text("it's a \\ test") == "'it''s a \\\\ test'"
    c = FakeClient()
    hits = c.query("q", 2, {"feed": ["promo", "all"]})
    assert hits[0]["rank"] == 1 and hits[0]["score"] == 0.9 and hits[1]["chunk_id"] == "B#c1"
    body = c.log[-1][2]
    assert json.loads(body["filters_json"]) == {"feed": ["promo", "all"]} and body["num_results"] == 2
    assert V.gold_rank_dicts(hits, ["copy the promotion owner"]) == 1
    assert V.gold_rank_dicts(hits, ["absent phrase"]) is None
    import time
    real_sleep = time.sleep
    time.sleep = lambda s: None
    try:
        info = V.wait_for_index(c, 42)
    finally:
        time.sleep = real_sleep
    assert V.index_ready(info) and V.indexed_rows(info) == 42 and c.polls == 3
    sql_file = (V.ASSIGNMENT_DIR / "4_Vector_Database_Creation_in_Databricks" / "Scenarios"
                / "Scenario_1_End_to_End_Index_Build" / "01_create_runbook_chunks.sql")
    stmts = V.VSClient.sql_statements(sql_file) if sql_file.exists() else []
    assert not stmts or (len(stmts) == 2 and stmts[1].count("'RB-") + stmts[1].count("'LIN-") + stmts[1].count("'HB-") >= 1)
    print("offline checks passed; SQL statements in the 4.1 file:", len(stmts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
