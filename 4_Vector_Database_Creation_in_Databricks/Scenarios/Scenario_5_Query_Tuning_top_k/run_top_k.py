"""Scenario 4.5: query tuning. The same questions at top_k = 3 and top_k = 15 on the Vector Search index.

Run from the repo (folder: Scenario_5_Query_Tuning_top_k):  python3 run_top_k.py | tee top_k_output.txt
Needs DATABRICKS_HOST and DATABRICKS_TOKEN in the environment (never in files).
Cost: 10 similarity queries (5 questions x 2 values) and 4 answer calls (Q1 and Q5, each with 3 and 15 passages).
Relevant chunk = a chunk that contains one of the question's gold phrases (test_questions.json, written before retrieval).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "vector"))
import vs_lib as V  # noqa: E402

R, S = V.R, V.S
SMALL, LARGE = 3, 15
ANSWER_FOR = {"Q1", "Q5"}


def relevant_ids(hits, phrases):
    wanted = [R.normalise_text(p) for p in phrases]
    return [h["chunk_id"] for h in hits if any(p in R.normalise_text(h["text"]) for p in wanted)]


def words(hits) -> int:
    return sum(len(h["text"].split()) for h in hits)


def main() -> int:
    R.setup_logging()
    client = V.VSClient()
    chat = R.DatabricksChat(client.base)
    summary = []
    for q in S.load_questions():
        V.out(f"=== {q['id']}: {q['question']}")
        runs = {}
        for k in (SMALL, LARGE):
            hits = client.query(q["question"], k)
            runs[k] = hits
            rank = V.gold_rank_dicts(hits, q["gold_phrases"])
            rel = relevant_ids(hits, q["gold_phrases"])
            V.out(f"-- top_k = {k}: first relevant rank = {rank}; relevant chunks = {len(rel)}; context words = {words(hits)}")
            V.show_hits(hits)
            V.out(f"   relevant: {rel}")
        same = [h["chunk_id"] for h in runs[SMALL]] == [h["chunk_id"] for h in runs[LARGE][:SMALL]]
        V.out(f"Top {SMALL} of the top_k={LARGE} run identical to the top_k={SMALL} run: {same}")
        answers = {}
        if q["id"] in ANSWER_FOR:
            for k in (SMALL, LARGE):
                hits = [V.hit_to_chunk_hit(h) for h in runs[k]]
                answer = chat.answer(q["question"], hits)
                cites = R.citation_check(answer, len(hits))
                facts = S.facts_ok(answer, q["must_contain"])
                answers[k] = (facts, cites)
                V.out(f"-- answer with top_k = {k}: {answer}")
                V.out(f"   key facts present = {facts}; citations valid = {cites['has_citation'] and cites['all_valid']}")
        V.out("")
        r3, r15 = runs[SMALL], runs[LARGE]
        g3, g15 = q["gold_phrases"], q["gold_phrases"]
        summary.append((q["id"], V.gold_rank_dicts(r3, g3), len(relevant_ids(r3, g3)), words(r3),
                        V.gold_rank_dicts(r15, g15), len(relevant_ids(r15, g15)), words(r15)))
    V.out("Summary")
    V.out("| question | first relevant rank (k=3) | relevant chunks (k=3) | context words (k=3) | first relevant rank (k=15) | relevant chunks (k=15) | context words (k=15) |")
    V.out("|---|---|---|---|---|---|---|")
    for row in summary:
        V.out("| " + " | ".join(str(x) for x in row) + " |")
    V.out(f"\nHTTP calls to Databricks REST by this run: {client.calls}; model-serving calls (answers): {client.base.calls}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
