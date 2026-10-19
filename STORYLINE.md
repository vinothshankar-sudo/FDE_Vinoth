# Fizzco Migration Assurance Hub: the single story behind all 31 scenarios

Status: approved storyline. All data, names and systems are synthetic. No client, Tiger or personal data.
Source assignment: `Data_Engineer_to_FDE_Readiness_Framework.md` (6 modules, 31 scenarios).

## 1. The story in one paragraph

Fizzco, a fictional beverages and snacks company, is retiring its legacy warehouse. A data engineer migrates four feeds (sell-in, sell-out, inventory, promotions) into a raw, trusted and gold data lake, and must prove nothing was lost. Analysts then ask business questions in plain English, support staff search runbooks when a job fails, leadership wants one screen showing migration health, and finally one agent combines all of it.

## 2. Personas and where each module serves them

| Persona | Need | Module |
|---|---|---|
| Data engineer (you) | Build, document and fix the pipelines faster | 1 |
| Commercial analyst | Ask "how are we selling vs the shelf?" | 2 |
| Support lead | "A job failed. What do I do?" | 3, 4 |
| Leadership | One screen of migration health | 5 |
| Everyone | An assistant that combines all of the above | 6 |

## 3. Shared vocabulary (identical in every module)

| Item | Value |
|---|---|
| Company | Fizzco Beverages & Snacks (fictional) |
| Feeds | `sell_in`, `sell_out`, `inventory`, `promo` |
| Layers | raw, trusted, gold |
| Storage container | `fizzco-landing` (renamed from `fizzco-raw` in scenario 1.2; the different container `fizzco-raw-archive` is archive only) |
| Pipelines | `pl_fizzco_<feed>_load` |
| IDs | `OBJ-###` objects, `JOB-####` jobs, `RECON-####` reconciliations, `PROMO-2026-####` promotions |
| Regions | East, West |
| Gold tables | `gold_sell_in_vs_sell_out`, `gold_recon_results`, `gold_promo_performance` |
| Recurring incident | The 31 March reconciliation mismatch (3 rows "missing") caused by an off-by-one date filter |

## 4. Traceability matrix (reviewer view)

| Scenario | Story moment | Artifact | Reused later in |
|---|---|---|---|
| 1.1 Prompt file | Document each pipeline's lineage | `/document-pipeline` prompt, 2 lineage docs | Docs feed the RAG corpus (3.1) |
| 1.2 Subagent | Rename the storage container across the estate | Subagent file list, diff, zero-stale-match proof | Same container name used in app config (5.1) |
| 1.3 Skill | Validate the object inventory before cutover | Skill, validator, 2 planted errors found | Inventory objects referenced by the agent (6.2) |
| 1.4 Standards | Team conventions for naming, errors, logging | Instructions file, audit table | Applied to all later code |
| 1.5 Bug loop | Fix the 31 March recon mismatch | Diagnosis, failing then passing test | **Reappears as the agent's hero question (6.2)** |
| 1.6 MCP | Read table schema from the system, not memory | Screenshot of MCP call | Same tables used by Genie (2.1) |
| 2.1 Genie space | Analysts query gold tables | Genie space, descriptions, 3+ sample SQLs | Back end of app tab (5.2) |
| 2.2 Break and fix | "Net sales" and "variance" have two meanings | Root cause and metadata fix | Definitions appear in KPI glossary (3.1) |
| 2.3 Governance | East and West managers see only their region | Two-identity test | Repeated in app (5.4) |
| 2.4 Genie API | Programmatic question and follow-up | Script returning generated SQL | Tool inside the agent (6.2) |
| 2.5 Business handoff | Vague ask "how is the market performing?" becomes a scoped demo | Scope decisions document | Opening screen of the app (5.2) |
| 3.1 Baseline RAG | Support asks about job failures | Q&A with citations over runbooks | Retriever for index (4.1) and agent (6.2) |
| 3.2 Chunking | 200 vs 800 token chunks | Comparison table | Chunk size chosen for 4.1 |
| 3.3 Metadata filter | Filter by feed or doc type | Filtered query | Filter reused in 4.3 |
| 3.4 Groundedness | Ask about something not documented | System says "not found" | Eval edge case (6.3) |
| 3.5 Hybrid search | Exact `JOB-0042` or `RECON-0007` lookup | Hybrid vs semantic comparison | Agent lookup (6.2) |
| 4.1 Index build | Index the runbook chunks | Endpoint and Delta Sync index | Retriever for app and agent |
| 4.2 Freshness | Add a new runbook, time its appearance | Timing note | Monitoring idea (6.5) |
| 4.3 Filtered search | Search within one feed | Filtered similarity query | Same as 3.3 at scale |
| 4.4 Index types | Delta Sync vs Direct Access | Tradeoff table | Rationale in README |
| 4.5 top_k | 3 vs 15 | Recommendation | Setting used by the agent |
| 5.1 Minimal app | Recon status from SQL warehouse | App, no hard-coded credentials | Tab 1 of the Hub |
| 5.2 Genie and RAG front end | Ask the data, ask the runbooks | Two more tabs | Same back ends as 2.1, 3.1 |
| 5.3 Failure handling | Endpoint down or slow | Friendly error state | Failure mode in eval (6.3) |
| 5.4 Access control | East vs West users | Two-user test | Mirrors 2.3 |
| 5.5 Live iteration | Filter, chart, export in 3 releases | 3 commits with validation notes | Final Hub |
| 6.1 First agent | Tool: `get_recon_status(feed, date)` | UC function and agent | Core tool |
| 6.2 Multi-tool | Genie plus runbook retriever plus recon tool; hero question: "Why did sell_in fail on 31 March and what do I do?" | Agent answering with data and runbook step | Ties 1.5, 2.4, 3.1, 4.1 together |
| 6.3 Evaluation | 10 to 15 questions, easy and edge | Eval set and one documented failure | Uses 3.4 and 5.3 cases |
| 6.4 Tracing | Break a tool, find the failing step | Trace and root-cause note | Debug story |
| 6.5 Deploy and monitor | Serving endpoint and monitoring approach | Endpoint and monitoring note | Hub can call it |

## 5. Repo layout

| Path | Contents |
|---|---|
| `README.md` | This story, the matrix above, and a status column |
| `module_1` to `module_6` | One folder each, with `README.md` using: Goal, Prompt, Result, Verification, Lesson |
| `shared/data_generation/` | Seeded generator for every synthetic table |
| `shared/docs_corpus/` | Synthetic runbooks, KPI glossary, recon policy, cutover checklist |
| `evidence/` | Screenshots grouped by scenario number (`s1_1`, `s2_3`, ...) |

## 6. Rules that keep it clean

| Rule | Why |
|---|---|
| Use only the shared vocabulary in section 3 | A reviewer can follow IDs from one module to the next |
| The traceability matrix above shows which scenarios reuse or feed each other | The reviewer sees the connection immediately |
| Seed all randomness (`SEED = 42`) | Results are reproducible |
| No secrets in any file; credentials via environment variables | Tiger responsible-AI rules |
| One scenario per commit | Easy review and rollback |
| Disclose AI use and review every output | Tiger responsible-AI rules |

