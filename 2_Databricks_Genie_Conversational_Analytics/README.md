# Module 2: Databricks Genie (Conversational Analytics)

Genie lets business users ask questions in plain English against governed Unity Catalog tables and get SQL-backed answers. It works inside a Genie space: a chosen set of tables plus descriptions and instructions that teach it the business terms. In this module I built and tested Genie spaces over the Fizzco gold tables.

## Scenarios

| # | Scenario | Status |
|---|---|---|
| 1 | [Build from scratch](#scenario-1-build-from-scratch) | Done |
| 2 | [Break and fix](#scenario-2-break-and-fix) | Done |
| 3 | [Governance check](#scenario-3-governance-check) | Done |
| 4 | [Programmatic access](#scenario-4-programmatic-access) | Done |
| 5 | [Business handoff](#scenario-5-business-handoff) | Done |

I worked on Databricks Free Edition in catalog `workspace`, schema `fizzco`. Each scenario folder under `Scenarios/` has the setup files and an `evidence/` folder with screenshots.

## Scenario 1: Build from scratch

Folder: `Scenarios/Scenario_1_Build_Genie_Space_from_Scratch/`

**Task:** create a Genie space over a gold table set, with table and column descriptions and at least 3 sample instructions.

**What I did:** built the space "Retail Sales & Promotions Analytics" over 4 tables (`gold_sell_in_vs_sell_out`, `gold_promo_performance`, `dim_retailer`, `dim_product`). I left out `gold_recon_results` on purpose, because it is a data-quality table for engineers. I wrote table and column comments (`table_column_descriptions.sql`), general instructions, and 5 example queries (`genie_space_setup.md`, `sample_questions.sql`).

**Result:** I computed an answer key from the CSV files before building the space (`sample_questions_expected.txt`). Genie matched it on all 5 questions plus 1 reworded question. For example, net sell-in by region was West 12,463.04 and East 9,893.50.

**Limits:** questions 1 to 5 use the same wording as the example titles, so Genie may have reused the example SQL. The reworded question 6 is the real test. The generated SQL is visible in the screenshots for questions 1 and 6 only.

**Lesson:** the setup (table scope, comments, short instructions) mattered more than the questions. A reworded question is a better test than an exact one.

## Scenario 2: Break and fix

Folder: `Scenarios/Scenario_2_Break_and_Fix_Ambiguous_Metric/`

**Task:** ask an ambiguous question that gives a wrong answer, find the cause, and fix it with better metadata, not by rewording the question.

**What I did:** the main space already answered "net sales" correctly, because its comments and examples carried the definition. So I built a break on purpose: a second space over a `legacy_sales` table with no comments, where the column `net_sales` actually holds shopper sales and the invoiced value is in `invoiced_amount`. This is a constructed ambiguity, not a Genie mistake. I asked "What were net sales by region?" before and after the fix.

**Result:**

| | West | East | Column used |
|---|---|---|---|
| Before (wrong) | 15,437.84 | 12,848.45 | `net_sales` |
| After (right) | 12,463.04 | 9,893.50 | `invoiced_amount` |

The fix was column and table comments (`02_fix_metadata.sql`), an instruction defining net sales (`03_genie_instruction_fix.md`), and an SQL expression plus an example query (`04_sql_expression_and_example.md`). Root cause is in `root_cause_note.md`.

**Limits:** "variance" was not broken, since Genie answered it correctly. I did not confirm with a screenshot that the comments on the baseline copy were cleared.

**Lesson:** Genie matches the words in a question to column names first. Fix the metadata, not the question, so it works for every future user.

## Scenario 3: Governance check

Folder: `Scenarios/Scenario_3_Governance_Check_Row_Level_Access/`

**Task:** test the same Genie space with two users who have different row-level permissions, and confirm the answers differ.

**What I did:** put a row filter on `region` for `gold_sell_in_vs_sell_out` and `gold_promo_performance` (`01_row_filter_template.sql`). The West manager sees West rows, the East manager sees East rows, anyone else sees none. I gave a second workspace user read access and `Can Run` on the space (`02_grants_template.sql`). Both users asked the same question: "What were net sell-in sales by region?"

**Result:** the work-account user saw only West (12,463.04) and the second user only East (9,893.50). The generated SQL has no region condition, so the filtering is done by Unity Catalog. 12,463.04 + 9,893.50 = 22,356.54, the full total, so rows were hidden, not lost.

**Limits:** two users, one run each. Emails are blacked out in the screenshots and replaced by placeholders in the SQL templates.

**Lesson:** put access control in Unity Catalog, not in Genie instructions. The filter also applies to the table owner, so it has to be removed when not needed (`03_rollback.sql`). I still need to run the rollback after Module 5 if the filter is on.

## Scenario 4: Programmatic access

Folder: `Scenarios/Scenario_4_Programmatic_Access_Genie_API/`

**Task:** use the Genie API to start a conversation, ask a follow-up in the same thread, and get the generated SQL, without the UI.

**What I did:** used the script `genie_api_demo.py` (drafted with AI help). It starts a conversation, asks "Now show only the East region, broken down by retailer.", polls until each message is complete, and prints the SQL and rows. Host, token and space id come from environment variables only. It retries rate limits and reports failed states.

**Result:** it ran once on 7 October 2026. Both questions finished in about 28 and 29 seconds in one conversation. Question 1 gave West 12,463.04 and East 9,893.50. For question 2 Genie joined `dim_retailer` and added the East filter itself. The five East retailers add up to 9,893.50, which matches question 1. Output files: `genie_api_output.txt` and `genie_api_run_log.txt`.

**Limits:** one run. Free Edition has no service principals, so I used a personal access token, and I revoked it afterwards.

**Lesson:** the API is asynchronous: start, then poll until completed. The generated SQL is part of the output, and the agent in Module 6 inherits the token user's access.

## Scenario 5: Business handoff

Folder: `Scenarios/Scenario_5_Business_Handoff_Vague_Ask_to_Demo/`

**Task:** turn a vague ask ("show me how markets are performing") into a working Genie demo in under an hour, with the scope decisions written down.

**What I did:** defined "markets" as Fizzco's own regions, channels and retailers, and "performing" as sell-through percentage. Built a new space, "Fizzco Market Performance Demo", with 2 tables, instructions and 2 example queries, in 20 minutes (my own timing). Scope choices are in `scope_decisions.md` and the setup in `genie_space_setup.md`. Reference SQL and expected results are in `demo_questions.sql` and `demo_questions_expected.txt`.

**Result:** all 5 tables and numbers matched my answer key. Genie correctly refused the market-share question. Two sentences in Genie's written commentary were wrong: it said the West was "stronger" although both regions have the same 88.9% sell-through, and it said March was the sales peak when January is higher. The finding for the stakeholder: regions look the same, and the gap is in supermarkets, which have the lowest channel sell-through (85.9%).

**Limits:** I did not capture a screenshot of the Examples tab, so "only D1 and D3 were added as examples" rests on me following the setup file. Genie shows amounts with a `$` sign although the data has no currency.

**Lesson:** scope is a deliverable. Check Genie's commentary and not only its tables, because the SQL was right every time but two sentences were not.

## AI use

I used an AI assistant to help draft the setup files, scripts and this README. I built the Genie spaces, ran the questions and the script myself, and checked the results against my answer key. The answers and SQL shown were generated by Genie (Databricks). All data is synthetic.
