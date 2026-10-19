# Module 3: Retrieval-Augmented Generation (RAG)

RAG grounds a language model's answer in real documents: it finds the relevant text first, then answers from it, with a citation. This module builds a small RAG pipeline over the Fizzco runbooks and tests how to make it better.

## Scenarios

| # | Scenario | Status |
|---|---|---|
| 1 | [Baseline pipeline](#scenario-1-baseline-pipeline) | Done |
| 2 | [Chunking tradeoffs](#scenario-2-chunking-tradeoffs) | Done |
| 3 | [Metadata-filtered retrieval](#scenario-3-metadata-filtered-retrieval) | Done |
| 4 | [Groundedness failure hunt](#scenario-4-groundedness-failure-hunt) | Done |
| 5 | [Hybrid retrieval](#scenario-5-hybrid-retrieval) | Done |

## Shared setup

| Item | Value |
|---|---|
| Documents | 14 synthetic documents (12 in `shared/docs_corpus/`, 2 lineage documents in `shared/fizzco_lake/docs/`) |
| Models | Databricks Foundation Model API: `databricks-gte-large-en` for embeddings, `databricks-meta-llama-3-3-70b-instruct` for answers (temperature 0) |
| Index | In memory (numpy, cosine similarity). The real Databricks index is built in Module 4 |
| Code | `shared/rag/rag_lib.py`, `shared/rag/rag_setup.py`; test questions in `shared/rag/test_questions.json` (written before any retrieval ran) |
| Credentials | `DATABRICKS_HOST` and `DATABRICKS_TOKEN` from environment variables only |

I ran the scripts from my Mac. The embedding endpoint hit a rate limit (HTTP 429) on the first run, so the scripts now send small batches, pause, and retry. All results are cached on disk, so a re-run costs nothing. Running a script with `RAG_CACHE_ONLY=1` replays it from the cache with no token, and it reproduced every saved output. Each scenario folder under `Scenarios/` has the script, the saved output and a screenshot of that replay.

## Scenario 1: Baseline pipeline

Folder: `Scenarios/Scenario_1_Baseline_RAG_Pipeline/`

**Task:** build a RAG pipeline over a small document set (chunk, embed, index, retrieve, answer) and answer 5 test questions with citations.

**What I did:** split the documents into 200-token pieces with 40 overlap (42 chunks), retrieved the top 3, and asked the model to answer only from them and cite each fact (`run_baseline_rag.py`, output in `baseline_rag_output.txt`).

**Result:** all 5 questions passed three checks (right chunk found, citations valid, key facts present). The right chunk was at rank 1, 1, 1, 1 and 3. For the sell_in question the answer said an off-by-one date filter excluded the end date and the fix was to make it inclusive, and I checked the cited text supports it.

**Limits:** five questions is a small test. The citation check proves the label exists, not that the sentence is supported, so I checked the main claims separately.

**Lesson:** question 5 needed rank 3, which is why top_k is 3 and not 1. Citations make an answer auditable.

## Scenario 2: Chunking tradeoffs

Folder: `Scenarios/Scenario_2_Chunking_Tradeoffs/`

**Task:** compare two chunking strategies on the same 5 questions and say which is better and why.

**What I did:** compared four settings, retrieval only (`run_chunking_comparison.py`).

| Size / overlap | Chunks | Right chunk in top 3 | MRR | Context words sent |
|---|---|---|---|---|
| 200 / 0 | 38 | 4 of 5 | 0.67 | 502 |
| 200 / 40 | 42 | 5 of 5 | 0.87 | 534 |
| 800 / 0 | 15 | 5 of 5 | 0.90 | 1,256 |
| 800 / 100 | 15 | 5 of 5 | 0.90 | 1,145 |

**Result:** 200 with 40 overlap wins for Module 4. It finds the answer for every question with about half the text of the 800 settings. Without overlap, 200/0 lost question 5 completely. At 800 most documents are one chunk, so the two 800 settings give the same result.

**Limits:** five questions and about 6,000 words. One rank step on one question moves MRR by 0.07 to 0.13, so read this as a direction, not a measurement. My reason for the question 5 miss is likely but not proven.

**Lesson:** pick chunk size from the shape of your documents. Small chunks need overlap.

## Scenario 3: Metadata-filtered retrieval

Folder: `Scenarios/Scenario_3_Metadata_Filtered_Retrieval/`

**Task:** add a metadata field and filter retrieval to the relevant subset before answering.

**What I did:** each chunk carries `feed` and `doc_type`. I ran four questions with and without a filter (`run_metadata_filter.py`). A feed filter also keeps documents marked `all`.

**Result:** the filter raised the share of results inside the wanted subset in 3 of 4 cases and moved the right chunk into the top 3 in 2 of 4. It changed nothing for F2, and it could not fix F3, a vague question ("common causes of a failed load") that was refused both ways. In F1 the answer still hedged, because the model is not told which feed was meant.

**Limits:** four cases is a demonstration, not a statistical test.

**Lesson:** a filter removes the wrong subset, but it does not make a vague question specific. Telling the model the scope is a next step.

## Scenario 4: Groundedness failure hunt

Folder: `Scenarios/Scenario_4_Groundedness_Failure_Hunt/`

**Task:** ask questions the documents do not answer, confirm the system says so, and fix the prompt if it doesn't.

**What I did:** asked three unanswerable questions (on-call engineer, a loyalty-card SLA, cloud region) plus one control, first with a plain prompt, then with the strict prompt (`run_groundedness.py`).

**Result:**
- With the plain prompt, one question (cloud region) got an unsupported guess built from an unrelated sentence about sales regions ("likely East or West"), and answers had no citations.
- With the strict prompt, all 3 refused with the fixed sentence "I could not find this in the Fizzco documents.", and the control was still answered with citations.
- A similarity cut-off would not work, because real answers scored as low as 0.63 and one unanswerable question scored 0.70.

**Limits:** three questions, none with partly related text. Harder cases are the first thing to add in Module 6.

**Lesson:** retrieval always returns something, so the prompt must say what to do when it isn't enough. A fixed refusal sentence makes "not found" testable.

## Scenario 5: Hybrid retrieval

Folder: `Scenarios/Scenario_5_Hybrid_Retrieval/`

**Task:** combine keyword and vector search for a query where vector search alone is weak, such as an exact ID, and show the improvement.

**What I did:** four ID questions (RECON-0007, JOB-0044, RECON-0012, JOB-0049) with vector only, keyword only (BM25), and hybrid (rank fusion) (`run_hybrid.py`).

| | Vector only | Keyword only | Hybrid |
|---|---|---|---|
| Found in top 3 | 3 of 4 | 4 of 4 | 4 of 4 |
| MRR | 0.58 | 1.00 | 0.83 |

**Result:** the clear win is RECON-0007. Vector search missed it and the model said it could not find it. Hybrid found it and the answer was correct (MATCH, job JOB-0047, 29 and 29 rows). I checked all four answers against the register.

**Limits:** four queries and one corpus. On these ID lookups keyword-only ranked best, and I did not test paraphrased questions where hybrid should do better.

**Lesson:** embeddings capture meaning, not exact strings, so IDs need keyword search. Plain rank fusion is a compromise.

## AI use

I used an AI assistant to help draft the documents, code and this README, and to check answers against the chunk text. I ran the scripts myself and reviewed the results. The answers shown are generated by the Databricks-hosted Llama model from retrieved chunks. All data is synthetic.
