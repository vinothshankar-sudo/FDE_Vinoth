# Assignment log

Running record of what was done, where the proof is, and the status. All data is synthetic. AI-generated output was reviewed by a human before inclusion.

## Module 1: Agentic AI Coding Assistants 

| Scenario | What was done | Proof (in the scenario folder) | Status |
|---|---|---|---|
| 1.1 Repeatable workflow | Made a `/document-pipeline` command as a prompt file and as a skill. Ran it on the sell_in and inventory pipelines | Prompt file, skill copy, 2 lineage documents, 4 screenshots | Done |
| 1.2 Context management with subagents | A read-only subagent found 11 matches in 8 files. The main session renamed `fizzco-raw` to `fizzco-landing` and left the archive container alone | Subagent file list, `rename_diff.patch`, `zero_stale_search.txt`, 2 screenshots | Done |
| 1.3 Packaging a skill | A `validate-inventory` skill with a validator (5 rules). It loaded from a plain request in a new chat and found the 2 planted errors | `SKILL.md`, validator copy, my 6 test runs, 3 screenshots (1 optional to add) | Done |
| 1.4 Enforcing standards automatically | An instructions file with 3 coding rules. Two unrelated requests both passed all 3 | Instructions copy, both outputs, audit table, 5 screenshots | Done |
| 1.5 Agentic loop discipline | Found why the 31 March run mismatched (the end date was counted differently) and approved a one-character fix. The test fails before and passes after, and the run now matches | Diagnosis log, test, patch, outputs, 3 screenshots | Done |
| 1.6 Live data grounding via MCP | Loaded the 3 trusted CSVs into SQLite and connected a read-only SQLite MCP server. Copilot answered the schema and row-count question with a visible tool call, and would not invent a share price | `load_sqlite.py`, `mcp.json`, `mcp_verification.txt`, 4 screenshots | Done |

## Module 2: Databricks Genie — Conversational Analytics

| Scenario | What was done | Proof (in the scenario folder) | Status |
|---|---|---|---|
| 2.1 Build from scratch | Built the Genie space "Retail Sales & Promotions Analytics" over 4 gold tables, with instructions and 5 example queries. 5 questions plus 1 reworded question all matched the answer key | Setup files, answer key, 10 screenshots | Done |
| 2.2 Break and fix | Genie answered 5 of 5 correctly, so I built a break: a `legacy_sales` table with a misleading `net_sales` column. Genie gave 15,437.84 / 12,848.45 instead of 12,463.04 / 9,893.50. Column comments, an instruction, a SQL expression and an example query fixed it | Wrong and fixed screenshots, SQL, root-cause note | Done |
| 2.3 Governance check | Added a row filter on region to two tables. Two workspace users asked the same question: one saw only West (12,463.04), the other only East (9,893.50) | Row-filter and grant SQL, rollback, 5 screenshots (emails blacked out) | Done |
| 2.4 Programmatic access | A Python script uses the Genie API: it starts a chat, asks a follow-up, and pulls out the SQL and rows. The token comes only from an environment variable. Results match 2.1 (West 12,463.04, East 9,893.50) | `genie_api_demo.py`, `genie_api_output.txt`, `genie_api_run_log.txt` | Done |
| 2.5 Business handoff | Turned the vague ask "how are markets performing" into a clear scope (regions, channels, retailers, sell-through). Built a new space, "Fizzco Market Performance Demo", in 20 minutes. 5 of 5 tables matched the key. Genie's commentary had 2 mistakes (called West stronger at equal sell-through; called March the peak when January is higher) and it correctly refused a market-share question | `scope_decisions.md`, `genie_space_setup.md`, `demo_questions.sql`, expected results, 6 screenshots | Done |

## Module 3: Retrieval-Augmented Generation (RAG)

| Scenario | What was done | Proof (in the scenario folder) | Status |
|---|---|---|---|
| 3.1 Baseline pipeline | 14 synthetic documents split into 200-token pieces (40 overlap). 5 support questions all found the right piece in the top 3, with valid citations | `run_baseline_rag.py`, `baseline_rag_output.txt` | Done |
| 3.2 Chunking tradeoffs | Tried four chunk settings on the same 5 questions. 200 with 40 overlap won: 5 of 5 in the top 3, with about half the context of 800 | `run_chunking_comparison.py`, `chunking_output.txt` | Done |
| 3.3 Metadata filter | Added `feed` and `doc_type` filters. Results improved in 3 of 4 cases and the right piece reached the top 3 in 2 of 4. One vague question was not fixed | `run_metadata_filter.py`, `metadata_filter_output.txt` | Done |
| 3.4 Groundedness | A plain prompt gave one unsupported guess (a cloud region) and uncited answers. A strict prompt refused 3 of 3 unsupported questions and still answered the control. A similarity cut-off did not work | `run_groundedness.py`, `groundedness_output.txt` | Done |
| 3.5 Hybrid retrieval | Mixed keyword and vector search on 4 ID lookups: vector found 3 of 4 in the top 3, the mix found 4 of 4. Keyword alone ranked best | `run_hybrid.py`, `hybrid_output.txt` | Done |

## Module 4: Vector Database Creation in Databricks

| Scenario | What was done | Proof (in the scenario folder) | Status |
|---|---|---|---|
| 4.1 End-to-end index build | Built the table `workspace.fizzco.runbook_chunks` (42 chunks), the endpoint `fizzco_vs` and the index `runbook_chunks_index`. The index was ready with 42 rows after about 20 minutes. The first query ranked the incident note first for the 31 March question | `01_create_runbook_chunks.sql`, `run_build_index.py`, `build_index_output.txt`, 4 screenshots | Done |
| 4.2 Freshness test | Added a test row and asked for one sync. The index stayed at 42 rows until the sync, then showed 43 after 82 s and ranked the new row first. Delete and sync took 72 s. Test row removed | `02_insert_new_runbook.sql`, `run_freshness.py`, output files, 3 screenshots | Done |
| 4.3 Filtered search | Ran the four 3.3 cases against the index with filters. Every result stayed inside the filter and the right chunk reached the top 3 in 1 of 4. One case differs from 3.3 (rank 4 instead of 3, a near tie) | `run_filtered_search.py`, output and diagnosis files, 3 screenshots | Done |
| 4.4 Index types | Created a Direct Vector Access index on the same endpoint (the Free Edition page says unsupported, but it worked). Same top 3 as Delta Sync. Update and delete took 2.7 s against 84 s and 72 s. I recommend Delta Sync for runbooks. Test index deleted | `run_direct_access.py`, output files, 3 screenshots | Done |
| 4.5 Query tuning | Same 5 questions with top_k 3 and 15: first relevant chunk at rank 1, 1, 1, 1, 3 both times, top 3 identical, but context grew from about 550 to about 2,500 words. I recommend top_k around 5 (a judgment from 5 questions) | `run_top_k.py`, `top_k_output.txt`, 4 screenshots | Done |

## Module 5: Databricks Apps

| Scenario | What was done | Proof (in the scenario folder) | Status |
|---|---|---|---|
| 5.1 Minimal deployable app | Deployed the Streamlit app `fizzco-hub`. It reads `workspace.fizzco.gold_recon_results` through a SQL warehouse as the app's own identity, with no credentials in files. 13 rows shown; 10 compared with the source CSV, all match | `app.py`, `app.yaml`, `requirements.txt`, `01_grants_template.sql`, 4 screenshots | Done |
| 5.2 Front-end for Genie/RAG | Added two tabs: Genie questions (answer, SQL, rows) and runbook questions (top 5 passages, answer, citation check). Genie gave West 12,463.04 and East 9,893.50. The runbook answer cited S1 and S2 and every claim was found in the passages | App files, `helpers.py`, `test_helpers.py`, 3 screenshots | Done |
| 5.3 Model-serving integration | The runbook tab waits at most 45 s, shows a plain message for each kind of error, and falls back to the top 3 passages. Live: a wrong endpoint name and a 1-second limit each gave the right message; a normal run was unchanged. 23 helper tests pass | App files, `helpers.py`, 2 test files, 4 screenshots | Done |
| 5.4 Access control test | A fourth tab runs one query twice: as the signed-in user and as the app's own identity. The row filter decides the rows. Live: the West user saw 37 rows (12,463.04), the East user 31 rows (9,893.5), the app's own identity none | App files, `01_row_filter_steps.sql`, 3 test files, 4 screenshots | Done |
| 5.5 Live iteration | Grew the Recon tab in three releases, each deployed and checked first: (1) status filter, counts 13, 12, 1; (2) bar chart of differing rows, one bar at RECON-0009; (3) CSV download with the row count on the button. Earlier tests pass on every release. The download was checked only offline | One folder per release with app, tests, `VALIDATION_NOTES.md`, 10 screenshots | Done|

## Module 6: Databricks Agent Creation (Mosaic AI Agent Framework)

| Scenario | What was done | Proof (in the scenario folder) | Status |
|---|---|---|---|
| 6.1 First tool-calling agent | A Unity Catalog function `get_recon_status` as a tool. The agent used it for both Fizzco questions and answered the greeting and 12 times 12 directly (4 of 4). The sell_in answer named RECON-0009 (mismatch) and RECON-0013 (match) | `nb_6_1_first_agent.py`, SQL file, 3 screenshots | Done |
| 6.2 Multi-tool composition | Added runbook search and Genie as tools. Each single-tool question used the right tool (Genie: West 12,463.04, East 9,893.50). The question that needs both tools took three runs and the answer is still incomplete | `nb_6_2_multi_tool.py`, 11 screenshots | Done |
| 6.3 Evaluation before trust | 12 test questions, three checks: facts 0.667, tools 0.917, AI judge 0.917. 5 of 12 failed (E1, E2 no row counts; E6 Genie timeout; M1 left out the failed run; X3 no search). Questions not changed after the run | `eval_set.csv`, `nb_6_3_evaluation.py`, 6 screenshots | Done |
| 6.4 Tracing and root cause | Pointed the function at an old copy of the table. Same question gave "no run found" with every step OK. The trace showed the tool was the problem, not the model. Restored it and the right answer came back | `nb_6_4_tracing_root_cause.py`, 9 screenshots | Done |
| 6.5 Deployment and monitoring | Deployed to a Model Serving endpoint (ready in about 9 minutes). 5 of 6 live requests worked; the empty request was rejected on purpose; the Genie tool failed on the endpoint (cause not confirmed). Monitoring shown with traces and metrics charts; no inference table | `nb_6_5_deploy_monitor.py`, 17 screenshots | Done|



