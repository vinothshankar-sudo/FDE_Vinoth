"""Scenario 3.4: groundedness failure hunt. Ask questions the documents do NOT answer.

Run from this folder:  python3 run_groundedness.py | tee groundedness_output.txt
Stage A: naive prompt (no refusal rule). Stage B: strict grounded prompt. Stage C (only if still needed):
strict prompt plus a similarity gate that refuses before calling the model when the best chunk is too weak.
The control question IS answered by the documents and must still be answered.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "rag"))
import rag_lib as R  # noqa: E402
import rag_setup as S  # noqa: E402

CHUNK_SIZE, CHUNK_OVERLAP, TOP_K = 200, 40, 3
CASES = [
    {"id": "U1", "kind": "unanswerable", "question": "Who is the on-call engineer this weekend and what is their phone number?"},
    {"id": "U2", "kind": "unanswerable", "question": "What is the recovery time SLA for the loyalty-card feed?"},
    {"id": "U3", "kind": "unanswerable", "question": "Which cloud region hosts the fizzco-landing container?"},
    {"id": "C1", "kind": "control", "question": "How many rows of difference are accepted for a reconciliation to count as MATCH?"},
]
STAGES = [("A naive prompt", R.NAIVE_SYSTEM_PROMPT), ("B strict grounded prompt", R.GROUNDED_SYSTEM_PROMPT)]


def main() -> int:
    R.setup_logging()
    R.LOGGER.info("step start: groundedness hunt")
    docs = S.load_docs()
    chunks = R.chunk_corpus(docs, CHUNK_SIZE, CHUNK_OVERLAP)
    embedder, chat, client = S.make_components(chunks)
    vector, _ = R.build_indexes(chunks, embedder)
    R.write_out("Best retrieval score per question (cosine similarity of the top chunk):")
    scores = {}
    for case in CASES:
        hits = vector.search(case["question"], TOP_K)
        scores[case["id"]] = hits[0].score
        R.write_out(f"  {case['id']} ({case['kind']}): top score {hits[0].score:.4f}, top chunk {hits[0].chunk.chunk_id}")
    R.write_out("")
    for stage, prompt in STAGES:
        R.write_out(f"##### Stage {stage}")
        for case in CASES:
            hits = vector.search(case["question"], TOP_K)
            answer = chat.answer(case["question"], hits, prompt)
            cites = R.citation_check(answer, len(hits))
            R.write_out(f"{case['id']} [{case['kind']}] {case['question']}")
            R.write_out(f"  answer: {answer}")
            R.write_out(f"  refused = {cites['refused']}; has citation = {cites['has_citation']}")
        R.write_out("")
    R.write_out("Human review of the answers above decides which unanswerable questions were hallucinated; see the README.")
    if client is not None:
        R.write_out(f"Endpoint calls made in this run: {client.calls} (cached results cost nothing).")
    R.LOGGER.info("step end: done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
