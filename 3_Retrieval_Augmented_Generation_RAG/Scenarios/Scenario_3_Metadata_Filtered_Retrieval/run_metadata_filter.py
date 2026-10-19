"""Scenario 3.3: metadata-filtered retrieval. Same question with and without a filter on feed or doc_type.

Run from this folder:  python3 run_metadata_filter.py | tee metadata_filter_output.txt
Chunk metadata: feed (sell_in, sell_out, inventory, promo, all), doc_type (runbook, policy, glossary, ...).
A feed filter keeps the chosen feed plus documents marked feed = all (policies and the general runbook).
Setting: 200-token chunks with 40 overlap, top_k = 3.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "rag"))
import rag_lib as R  # noqa: E402
import rag_setup as S  # noqa: E402

CHUNK_SIZE, CHUNK_OVERLAP, TOP_K = 200, 40, 3
CASES = [
    {"id": "F1", "question": "A row was rejected during the load. Who should receive the reject file?",
     "filters": {"feed": ["promo", "all"]}, "target": "promo",
     "gold_phrases": ["copy the promotion owner", "Promotion data belongs to the commercial team"]},
    {"id": "F2", "question": "The job failed at the copy step. What should I check first?",
     "filters": {"feed": ["inventory", "all"]}, "target": "inventory",
     "gold_phrases": ["check that the snapshot file for the load_date exists"]},
    {"id": "F3", "question": "What are the common causes of a failed load?",
     "filters": {"feed": ["sell_out", "all"]}, "target": "sell_out",
     "gold_phrases": ["Late retailer scan file"]},
    {"id": "F4", "question": "What does MATCH mean?",
     "filters": {"doc_type": ["glossary"]}, "target": "glossary",
     "gold_phrases": ["Status is MATCH when the difference is zero"]},
]


def purity(hits, case) -> float:
    key = "doc_type" if "doc_type" in case["filters"] else "feed"
    ok = set(case["filters"][key])
    return sum(1 for h in hits if getattr(h.chunk, key) in ok) / len(hits)


def main() -> int:
    R.setup_logging()
    R.LOGGER.info("step start: metadata-filtered retrieval")
    docs = S.load_docs()
    chunks = R.chunk_corpus(docs, CHUNK_SIZE, CHUNK_OVERLAP)
    embedder, chat, client = S.make_components(chunks)
    vector, _ = R.build_indexes(chunks, embedder)
    rows = []
    for case in CASES:
        R.write_out(f"=== {case['id']}: {case['question']}   filter = {case['filters']}")
        results = {}
        for label, filters in (("unfiltered", None), ("filtered", case["filters"])):
            hits = vector.search(case["question"], TOP_K, filters)
            answer = chat.answer(case["question"], hits)
            rank = R.gold_rank(hits, case["gold_phrases"])
            results[label] = (hits, answer, rank)
            R.write_out(f"-- {label}:\n" + S.format_hits(hits))
            R.write_out(f"   answer: {answer}")
            R.write_out(f"   gold chunk rank = {rank}; share of top-3 inside the wanted subset = {purity(hits, case):.2f}")
        rows.append((case["id"], results["unfiltered"][2], results["filtered"][2], purity(results["unfiltered"][0], case), purity(results["filtered"][0], case)))
        R.write_out("")
    R.write_out("Summary")
    R.write_out("| case | gold rank unfiltered | gold rank filtered | in-subset share unfiltered | in-subset share filtered |")
    R.write_out("|---|---|---|---|---|")
    for cid, ru, rf, pu, pf in rows:
        R.write_out(f"| {cid} | {ru} | {rf} | {pu:.2f} | {pf:.2f} |")
    if client is not None:
        R.write_out(f"Endpoint calls made in this run: {client.calls} (cached results cost nothing).")
    R.LOGGER.info("step end: done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
