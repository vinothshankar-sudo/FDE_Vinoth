# Fizzco Migration Assurance Hub: the single story behind all 31 scenarios

Status: All data, names and systems are synthetic. No client, Tiger or personal data.
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


## 4. Repo layout

| Path | Contents |
|---|---|
| `README.md` | This story, the matrix above, and a status column |
| `module_1` to `module_6` | One folder each, with `README.md` using: Goal, Prompt, Result, Verification, Lesson |
| `shared/data_generation/` | Seeded generator for every synthetic table |
| `shared/docs_corpus/` | Synthetic runbooks, KPI glossary, recon policy, cutover checklist |
| `evidence/` | Screenshots grouped by scenario number (`s1_1`, `s2_3`, ...) |



