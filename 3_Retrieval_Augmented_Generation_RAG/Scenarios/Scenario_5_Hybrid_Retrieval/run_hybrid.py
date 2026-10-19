"""Scenario 3.5: hybrid retrieval. Exact JOB-#### / RECON-#### lookups: vector only vs keyword only vs hybrid.

Run from this folder:  python3 run_hybrid.py | tee hybrid_output.txt
Hybrid = reciprocal rank fusion (k = 60) of the vector ranking and the BM25 keyword ranking.
Setting: 200-token chunks with 40 overlap, top_k = 3.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "rag"))
import rag_lib as R  # noqa: E402
import rag_setup as S  # noqa: E402

CHUNK_SIZE, CHUNK_OVERLAP, TOP_K = 200, 40, 3
CASES = [
    {"id": "H1", "question": "What is the status of RECON-0007?", "gold": ["RECON-0007 is job JOB-0047"], "must": [["inventory"], ["MATCH"]]},
    {"id": "H2", "question": "Which feed did job JOB-0044 reconcile, and what was the result?", "gold": ["JOB-0044, feed promo"], "must": [["promo"], ["MATCH"]]},
    {"id": "H3", "question": "Show RECON-0012", "gold": ["RECON-0012 is job JOB-0052"], "must": [["promo"], ["MATCH"]]},
    {"id": "H4", "question": "What happened in JOB-0049?", "gold": ["JOB-0049"], "must": [["MISMATCH"], ["sell_in"]]},
]


def main() -> int:
    R.setup_logging()
    R.LOGGER.info("step start: hybrid retrieval")
    docs = S.load_docs()
    chunks = R.chunk_corpus(docs, CHUNK_SIZE, CHUNK_OVERLAP)
    embedder, chat, client = S.make_components(chunks)
    vector, keyword = R.build_indexes(chunks, embedder)
    table = []
    for case in CASES:
        R.write_out(f"=== {case['id']}: {case['question']}")
        row = [case["id"]]
        for label, search in (("vector only", lambda q: vector.search(q, TOP_K)),
                              ("keyword only (BM25)", lambda q: keyword.search(q, TOP_K)),
                              ("hybrid (RRF)", lambda q: R.hybrid_search(vector, keyword, q, TOP_K))):
            hits = search(case["question"])
            rank = R.gold_rank(hits, case["gold"])
            row.append(rank)
            R.write_out(f"-- {label}: gold chunk rank = {rank}\n" + S.format_hits(hits))
            if label != "keyword only (BM25)":
                answer = chat.answer(case["question"], hits)
                R.write_out(f"   answer ({label}): {answer}")
                R.write_out(f"   key facts in answer = {S.facts_ok(answer, case['must'])}")
        table.append(row)
        R.write_out("")
    R.write_out("Summary: rank of the chunk that holds the exact id (None = not in top 3)")
    R.write_out("| case | vector only | keyword only | hybrid |")
    R.write_out("|---|---|---|---|")
    for cid, v, k, h in table:
        R.write_out(f"| {cid} | {v} | {k} | {h} |")
    if client is not None:
        R.write_out(f"Endpoint calls made in this run: {client.calls} (cached results cost nothing).")
    R.LOGGER.info("step end: done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
