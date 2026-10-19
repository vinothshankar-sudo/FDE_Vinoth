"""Scenario 4.3: filtered similarity search on the Vector Search index (same four cases as Scenario 3.3, now at index scale).

Run from the repo (folder: Scenario_3_Filtered_Search):  python3 run_filtered_search.py | tee filtered_search_output.txt
Needs DATABRICKS_HOST and DATABRICKS_TOKEN in the environment (never in files).
Filters go to the index as filters_json, e.g. {"feed": ["promo", "all"]} (a list means "any of these values").
Cost: 8 similarity queries (4 cases, with and without filter), top_k = 3, no chat calls.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "vector"))
import vs_lib as V  # noqa: E402

TOP_K = 3
CASES = [
    {"id": "F1", "question": "A row was rejected during the load. Who should receive the reject file?",
     "filters": {"feed": ["promo", "all"]},
     "gold_phrases": ["copy the promotion owner", "Promotion data belongs to the commercial team"]},
    {"id": "F2", "question": "The job failed at the copy step. What should I check first?",
     "filters": {"feed": ["inventory", "all"]},
     "gold_phrases": ["check that the snapshot file for the load_date exists"]},
    {"id": "F3", "question": "What are the common causes of a failed load?",
     "filters": {"feed": ["sell_out", "all"]},
     "gold_phrases": ["Late retailer scan file"]},
    {"id": "F4", "question": "What does MATCH mean?",
     "filters": {"doc_type": ["glossary"]},
     "gold_phrases": ["Status is MATCH when the difference is zero"]},
]
# Scenario 3.3 results with the in-memory index, for comparison: (gold rank unfiltered, gold rank filtered)
MODULE3 = {"F1": (None, 3), "F2": (3, 3), "F3": (None, None), "F4": (None, 2)}


def share_in_subset(hits, filters) -> float:
    key = next(iter(filters))
    allowed = set(filters[key])
    return sum(1 for h in hits if h.get(key) in allowed) / len(hits) if hits else 0.0


def main() -> int:
    V.R.setup_logging()
    client = V.VSClient()
    V.out(f"Index: {V.INDEX}   top_k = {TOP_K}\n")
    rows = []
    for case in CASES:
        V.out(f"=== {case['id']}: {case['question']}   filter = {case['filters']}")
        result = {}
        for label, flt in (("unfiltered", None), ("filtered", case["filters"])):
            hits = client.query(case["question"], TOP_K, flt)
            rank = V.gold_rank_dicts(hits, case["gold_phrases"])
            share = share_in_subset(hits, case["filters"])
            result[label] = (rank, share)
            V.out(f"-- {label}:")
            V.show_hits(hits)
            V.out(f"   gold chunk rank = {rank}; share of top-3 inside the wanted subset = {share:.2f}")
        rows.append((case["id"], result["unfiltered"], result["filtered"]))
        V.out("")
    V.out("Summary (Vector Search index)")
    V.out("| case | gold rank unfiltered | gold rank filtered | in-subset share unfiltered | in-subset share filtered | Scenario 3.3 ranks (unfiltered, filtered) |")
    V.out("|---|---|---|---|---|---|")
    for cid, (ru, pu), (rf, pf) in rows:
        V.out(f"| {cid} | {ru} | {rf} | {pu:.2f} | {pf:.2f} | {MODULE3[cid]} |")
    V.out(f"\nHTTP calls made by this run: {client.calls}")
    return 0


def diagnose() -> int:
    """Two extra queries to understand why F1 (filtered) missed the promo runbook chunk that the in-memory index found at rank 3."""
    V.R.setup_logging()
    client = V.VSClient()
    case = CASES[0]
    V.out(f"Diagnosis of {case['id']}: {case['question']}")
    for label, flt, k in (("filter feed in [promo, all], top_k = 8", {"feed": ["promo", "all"]}, 8),
                          ("filter feed in [promo] only, top_k = 3", {"feed": ["promo"]}, 3)):
        hits = client.query(case["question"], k, flt)
        V.out(f"-- {label}:")
        V.show_hits(hits)
        V.out(f"   gold chunk rank = {V.gold_rank_dicts(hits, case['gold_phrases'])}")
    V.out(f"HTTP calls made by this run: {client.calls}")
    return 0


if __name__ == "__main__":
    sys.exit(diagnose() if len(sys.argv) > 1 and sys.argv[1] == "diagnose" else main())
