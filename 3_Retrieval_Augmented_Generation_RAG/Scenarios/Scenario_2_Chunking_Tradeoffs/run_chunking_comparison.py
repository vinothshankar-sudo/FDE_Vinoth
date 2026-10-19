"""Scenario 3.2: compare four chunking strategies on the same 5 questions (retrieval only).

Run from this folder:  python3 run_chunking_comparison.py | tee chunking_output.txt
Strategies: 200/0, 200/40, 800/0, 800/100 (size in tokens = words, overlap in tokens). top_k = 3.
Measures: hit@1, hit@3, mean reciprocal rank (MRR), words sent to the model for top 3, and
precision@3 = share of the top-3 chunk words that sit in the gold document.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "rag"))
import rag_lib as R  # noqa: E402
import rag_setup as S  # noqa: E402

STRATEGIES = [(200, 0), (200, 40), (800, 0), (800, 100)]
TOP_K = 3


def main() -> int:
    R.setup_logging()
    R.LOGGER.info("step start: chunking comparison")
    docs = S.load_docs()
    questions = S.load_questions()
    embedder = client = None
    summary = []
    for size, overlap in STRATEGIES:
        chunks = R.chunk_corpus(docs, size, overlap)
        if embedder is None:
            embedder, _, client = S.make_components(chunks)
        elif S.mode() == "offline":
            embedder, _, _ = S.make_components(chunks)
        vector, _ = R.build_indexes(chunks, embedder)
        R.write_out(f"--- Strategy size={size} overlap={overlap}: {len(chunks)} chunks, average {sum(c.n_tokens for c in chunks) / len(chunks):.0f} tokens")
        ranks, ctx_words, precisions = [], [], []
        for q in questions:
            hits = vector.search(q["question"], TOP_K)
            rank = R.gold_rank(hits, q["gold_phrases"])
            words = sum(h.chunk.n_tokens for h in hits)
            in_gold = sum(h.chunk.n_tokens for h in hits if h.chunk.doc_id == q["gold_doc"])
            ranks.append(rank)
            ctx_words.append(words)
            precisions.append(in_gold / words)
            top = hits[0].chunk
            R.write_out(f"  {q['id']}: gold chunk rank = {rank}; top-1 = {top.chunk_id}; context words = {words}; precision@3 = {in_gold / words:.2f}")
        hit1 = sum(1 for r in ranks if r == 1)
        hit3 = sum(1 for r in ranks if r is not None)
        mrr = sum(1.0 / r for r in ranks if r) / len(ranks)
        summary.append((size, overlap, len(chunks), hit1, hit3, mrr, sum(ctx_words) / len(ctx_words), sum(precisions) / len(precisions)))
        R.write_out("")
    R.write_out("Summary (5 questions, top_k = 3)")
    R.write_out("| size | overlap | chunks | hit@1 | hit@3 | MRR | avg context words | avg precision@3 |")
    R.write_out("|---|---|---|---|---|---|---|---|")
    for size, overlap, n, h1, h3, mrr, ctx, prec in summary:
        R.write_out(f"| {size} | {overlap} | {n} | {h1}/5 | {h3}/5 | {mrr:.2f} | {ctx:.0f} | {prec:.2f} |")
    if client is not None:
        R.write_out(f"Endpoint calls made in this run: {client.calls} (cached results cost nothing).")
    R.LOGGER.info("step end: done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
