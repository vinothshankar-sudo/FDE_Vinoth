# FDE Assignment: Fizzco Migration Assurance Hub

One made-up company (Fizzco) and one story run through all 6 modules and 31 scenarios. The story is in [STORYLINE.md](STORYLINE.md).

All data is synthetic. There are no secrets in any file. I used an AI assistant to help build and write this, and I ran and checked the work myself.

## Modules

| # | Module | Scenarios | Status |
|---|---|---|---|
| 1 | [AI coding assistants](1_Agentic_AI_Coding_Assistants/README.md) | 6 | Done |
| 2 | [Databricks Genie](2_Databricks_Genie_Conversational_Analytics/README.md) | 5 | Done |
| 3 | [Retrieval-Augmented Generation](3_Retrieval_Augmented_Generation_RAG/README.md) | 5 | Done |
| 4 | [Vector search](4_Vector_Database_Creation_in_Databricks/README.md) | 5 | Done |
| 5 | [Databricks Apps](5_Databricks_Apps/README.md) | 5 | Done |
| 6 | [Agent creation](6_Databricks_Agent_Creation_Mosaic_AI_Agent_Framework/README.md) | 5 | Done |

## Folders

- Each module has its own folder with one README and a `Scenarios` folder.
- Each scenario has the files I made and an `evidence` folder with screenshots.
- `shared/` has the synthetic data and documents used across modules (see below).

## Shared files

| Folder | What it holds |
|---|---|
| `shared/fizzco_lake/` | Synthetic ADF-style pipelines, notebooks, table scripts and CSV data. The gold data is made by `generate_gold_data.py` (SEED = 42), and the Unity Catalog setup script is `ddl/uc_gold_tables.sql`. Run scripts from inside this folder because paths are relative |
| `shared/inventory/` | Synthetic object inventory (with 2 planted errors) and an empty template |
| `shared/docs_corpus/` | 12 synthetic documents used by Modules 3, 4 and 6: runbooks for each feed, the 31 March incident note, the job register, recon policy, KPI glossary, cutover checklist, data dictionary and migration handbook. Each starts with a header (`doc_id`, `title`, `doc_type`, `feed`). Some facts are left out on purpose (on-call names, SLAs, a loyalty-card feed, cloud region) so scenario 3.4 can test refusals |
| `shared/rag/`, `shared/vector/` | The Python helpers used by Modules 3 and 4 |

All content is made up. The documents were drafted with an AI assistant and checked by me against the synthetic data (job and reconciliation ids come from `gold_recon_results.csv`).
