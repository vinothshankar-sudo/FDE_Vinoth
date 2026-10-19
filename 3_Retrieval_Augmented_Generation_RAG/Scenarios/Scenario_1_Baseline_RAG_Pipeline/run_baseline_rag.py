"""Scenario 3.1: baseline RAG pipeline. Chunk, embed, index, retrieve, answer 5 questions with citations.

Run from this folder:  python3 run_baseline_rag.py | tee baseline_rag_output.txt
Needs DATABRICKS_HOST and DATABRICKS_TOKEN in the environment (never in the code).
Setting: chunks of 200 tokens (words) with 40 overlap, top_k = 3, strict grounded prompt.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "rag"))
import rag_lib as R  # noqa: E402
import rag_setup as S  # noqa: E402

CHUNK_SIZE, CHUNK_OVERLAP, TOP_K = 200, 40, 3


def main() -> int:
    R.setup_logging()
    R.LOGGER.info("step start: baseline RAG")
    docs = S.load_docs()
    chunks = R.chunk_corpus(docs, CHUNK_SIZE, CHUNK_OVERLAP)
    embedder, chat, client = S.make_components(chunks)
    vector, _ = R.build_indexes(chunks, embedder)
    R.write_out(f"Corpus: {len(docs)} documents, {len(chunks)} chunks (size {CHUNK_SIZE}, overlap {CHUNK_OVERLAP}), top_k {TOP_K}")
    R.write_out(f"Embedding: {embedder.name}   Answering: {chat.name}\n")
    passed = 0
    for q in S.load_questions():
        hits = vector.search(q["question"], TOP_K)
        answer = chat.answer(q["question"], hits)
        cites = R.citation_check(answer, len(hits))
        rank = R.gold_rank(hits, q["gold_phrases"])
        facts = S.facts_ok(answer, q["must_contain"])
        ok = rank is not None and cites["has_citation"] and cites["all_valid"] and facts
        passed += ok
        R.write_out(f"=== {q['id']}: {q['question']}")
        R.write_out("Retrieved (top 3):\n" + S.format_hits(hits))
        R.write_out(f"Answer: {answer}")
        R.write_out("Sources cited:")
        for label in cites["labels"]:
            if 1 <= int(label[1:]) <= len(hits):
                c = hits[int(label[1:]) - 1].chunk
                R.write_out(f"  [{label}] {c.chunk_id} | {c.title} | {c.section} | \"{S.excerpt(c.text)}\"")
        R.write_out(f"Checks: gold chunk in top 3 = {rank is not None} (rank {rank}); citations valid = {cites['has_citation'] and cites['all_valid']}; key facts in answer = {facts}; PASS = {ok}\n")
    R.write_out(f"Summary: {passed} of {len(S.load_questions())} questions pass all three checks.")
    if client is not None:
        R.write_out(f"Endpoint calls made in this run: {client.calls} (cached results cost nothing).")
    R.LOGGER.info("step end: done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
