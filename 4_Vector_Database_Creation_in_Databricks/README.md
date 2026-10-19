# Module 4: Vector Database Creation in Databricks

Databricks Vector Search is the managed vector database that powers RAG and semantic search on governed Delta tables. In this module I moved the Fizzco runbook search from Module 3 into a real index and tested how it behaves.

## Scenarios

| # | Scenario | Status |
|---|---|---|
| 1 | [End-to-end index build](#scenario-1-end-to-end-index-build) | Done |
| 2 | [Freshness test](#scenario-2-freshness-test) | Done |
| 3 | [Filtered search](#scenario-3-filtered-search) | Done |
| 4 | [Index type comparison](#scenario-4-index-type-comparison) | Done |
| 5 | [Query tuning (top_k)](#scenario-5-query-tuning-top_k) | Done |

I ran the scripts from my Mac against the Databricks Free Edition REST APIs. The token comes only from environment variables and is never stored in a file. Each scenario folder under `Scenarios/` has the script, the saved output and an `evidence/` folder with screenshots.

## Scenario 1: End-to-end index build

Folder: `Scenarios/Scenario_1_End_to_End_Index_Build/`

**Task:** from a Delta table with change data feed on, create a Vector Search endpoint and a Delta Sync index, and run a similarity query.

**What I did:** created the table `workspace.fizzco.runbook_chunks` (42 chunks of the 14 runbook documents, `01_create_runbook_chunks.sql`), the endpoint `fizzco_vs`, and the Delta Sync index `runbook_chunks_index` (triggered sync, Databricks creates the embeddings with `databricks-gte-large-en`). The script is `run_build_index.py`, output in `build_index_output.txt`.

**Result:** the index was ready with 42 rows after about 20 minutes. For "Why did the sell_in reconciliation fail on 31 March 2026, and how was it fixed?" the top result was the incident note (`INC-2026-03-31-001#c1`), then `RB-SELL-IN-001#c3` and `INC-2026-03-31-001#c3`. This is the same top result as the in-memory search in Module 3.

**Problems:** the endpoint showed ONLINE two seconds after I created it, but the index waited about 14 minutes for it. The script now waits for the index to be ready with 42 rows, not for the endpoint flag. Piped output also appeared only at the end (buffering), so the helper now prints every line straight away.

**Limits:** one query is a smoke test, not a quality test. Free Edition allows one endpoint, so all of Module 4 reuses it.

**Lesson:** readiness is decided by the index status, not the endpoint flag. Create the table with change data feed on from the start.

## Scenario 2: Freshness test

Folder: `Scenarios/Scenario_2_Freshness_Test/`

**Task:** insert a new row after the index is built and time how long until it can be found.

**What I did:** inserted a synthetic "TEST ONLY" runbook (`02_insert_new_runbook.sql`), then timed the sync and the search with `run_freshness.py`. Afterwards I deleted the row and timed that too.

**Result:**

| Step | Time |
|---|---|
| Index right after the insert, no sync asked for | Still 42 rows |
| Sync requested until the index has 43 rows | 82 s |
| First query that finds the new row | 84 s after the sync request; it ranked first |
| Delete and sync until the row is gone | 72 s |

A triggered index does not update by itself, so a new runbook stays invisible until someone asks for a sync.

**Limits:** one run each way, timed to about 10 seconds. Continuous sync and updating existing rows were not tested.

**Lesson:** freshness is the wait until someone requests a sync plus about 80 seconds. A monitoring idea for later: compare the table row count with the index row count and alert if they differ for too long. The test row was removed straight away so it could not affect later scenarios.

## Scenario 3: Filtered search

Folder: `Scenarios/Scenario_3_Filtered_Search/`

**Task:** combine vector similarity with a metadata filter.

**What I did:** ran the four Module 3.3 cases against the real index with a filter on `feed` or `doc_type` (`run_filtered_search.py`, output files in the folder). The `feed` and `doc_type` columns were already in the table from 4.1, so I did not add a column afterwards.

**Result:** every filtered result was inside the filter in all 4 cases. The right chunk reached the top 3 in 1 of 4 cases (the glossary question went from not found to rank 2), against 2 of 4 in Module 3. One case (F1) differs from 3.3: the promo chunk is at rank 4, a near tie just outside the top 3. With a promo-only filter it is at rank 1, so the filter is not at fault.

**Limits:** four cases, one run, retrieval only. I did not test why the near tie came out differently, so I don't claim a reason.

**Lesson:** filtering that keeps the general documents leaves them crowding the list, since they are about half the corpus. Filtering fixes "wrong subset", not "vague question".

## Scenario 4: Index type comparison

Folder: `Scenarios/Scenario_4_Index_Type_Comparison/`

**Task:** build a Delta Sync index and a Direct Vector Access index and compare them.

**What I did:** created a Direct Access index on the same endpoint and loaded it with the same 42 chunks (`run_direct_access.py`). The Free Edition limits page says Direct Access is unsupported, but the workspace accepted it, so I report what I measured and say the limit may change.

**Result:**

| | Delta Sync | Direct Access |
|---|---|---|
| Top 3 for the same question | Same three chunks in the same order | Same |
| Add one row | About 84 s after the sync request | 2.7 s |
| Delete one row | About 72 s | 2.7 s |
| Who makes the vectors | Databricks | I do |
| Source of truth | The Delta table (governed) | The index itself |

I recommend keeping Delta Sync for the runbooks, because they change rarely and the table gives a record of where each row came from. Direct Access suits something that must be searchable within seconds. I deleted the test index afterwards.

**Problems:** my first freshness run stopped at the delete step because the script used the wrong REST method (HTTP 404). I fixed the script and the second run removed the leftover row first. The first run is kept as a transcript.

**Limits:** 42 rows, one measured run per operation. Embedding time for Direct Access is not counted, because I reused cached vectors.

**Lesson:** check what the platform really does, not only what the docs say. Direct Access trades governance for speed.

## Scenario 5: Query tuning (top_k)

Folder: `Scenarios/Scenario_5_Query_Tuning_top_k/`

**Task:** compare `top_k` 3 and 15 for the same questions and say how to choose it.

**What I did:** ran the five Module 3 questions at both settings (`run_top_k.py`, `top_k_output.txt`) and generated answers for two of them at both settings.

**Result:**
- The first relevant chunk was at rank 1, 1, 1, 1 and 3, the same at both settings. The top 3 never changed.
- Going to 15 made the context four to five times longer (from about 550 to about 2,500 words) and the extra relevant chunks only appeared at ranks 5 to 9.
- Both k=3 answers were correct with valid citations. At k=15 one answer gained a detail and one lost a step.
- Question 5 had its first relevant chunk at rank 3, so k=3 had no margin.

My recommendation is `top_k` around 5: a margin above the worst rank seen (3) without the extra noise. This is a judgment from five questions, not a proven best value. The k=5 context size is an estimate.

**Limits:** five questions, one run, answers for two of them. No re-ranker or latency test.

**Lesson:** a larger `top_k` added words, not a better first hit. The real risk was at the small end, so pick k from the worst observed rank plus a margin, and re-test when chunking or the corpus changes.

## AI use

I used an AI assistant to help write the scripts and this README. I ran everything on my own Databricks workspace, took the screenshots, and checked the numbers against the saved output files and screenshots. All data is synthetic, including the TEST ONLY runbook. Emails in the table and Catalog screenshots are blacked out.
