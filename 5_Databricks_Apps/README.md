# Module 5: Databricks Apps

Databricks Apps let you build and host a small web app (Streamlit, Gradio, Dash or Flask) inside the workspace, with governed access to Unity Catalog data and model endpoints. In this module I built one app, `fizzco-hub`, over five scenarios. Each scenario adds to it.

## Scenarios

| # | Scenario | Status |
|---|---|---|
| 1 | [Minimal deployable app](#scenario-1-minimal-deployable-app) | Done |
| 2 | [Front-end for Genie and RAG](#scenario-2-front-end-for-genie-and-rag) | Done |
| 3 | [Model-serving integration](#scenario-3-model-serving-integration) | Done |
| 4 | [Access control test](#scenario-4-access-control-test) | Done |
| 5 | [Live iteration](#scenario-5-live-iteration) | Done (3 commits at push) |

Everything runs on Databricks Free Edition. Each scenario folder under `Scenarios/` has the app files and an `evidence/` folder with screenshots.

## Scenario 1: Minimal deployable app

Folder: `Scenarios/Scenario_1_Minimal_Deployable_App/`

**Task:** deploy a basic app that runs a query on a SQL warehouse and shows the result, with no hardcoded credentials.

**What I did:** a Streamlit app (`app.py`) reads `workspace.fizzco.gold_recon_results` through the SQL warehouse attached as an app resource. The app runs as its own service principal, which I gave `SELECT` on the table. No token or password is in any file (`app.yaml`, `requirements.txt`, `01_grants_template.sql`).

**Result:** the app log says it fetched 13 rows. I compared the 10 visible rows with the source CSV and they all match. For 31 March, sell_in shows RECON-0009 (63, 60, 3 different, MISMATCH) and the rerun RECON-0013 (63 and 63, MATCH).

**Problems:** the first deploy failed with a platform timeout while copying the source, and the second worked. `GRANT` to the app's display name failed with `PRINCIPAL_DOES_NOT_EXIST`, so I granted from Catalog by picking the principal from the list. I also found and fixed one bug before deploying (`sql.exceptions.Error` does not exist in the connector).

**Limits:** one page load. Rows 11 to 13 are proven by the log line, not a screenshot. Packages are not pinned.

**Lesson:** give the app an identity, not a key. Access is then a Unity Catalog grant that can be shown and revoked.

## Scenario 2: Front-end for Genie and RAG

Folder: `Scenarios/Scenario_2_Front_End_for_Genie_and_RAG/`

**Task:** add a small UI where a user types a question and gets an answer from Genie or from the RAG pipeline.

**What I did:** the app now has three tabs: recon table, "Ask the data" (Genie) and "Ask the runbooks" (RAG). The runbooks tab fetches the top 5 passages from the vector index, asks the Llama model to answer only from them, and checks that every cited label exists. Files: `app.py`, `helpers.py`, `test_helpers.py` (15 offline tests).

**Result:** Genie answered "12,463.04 in the West and 9,893.50 in the East", with its SQL, matching the Module 2 answer key. The runbooks answer explained the off-by-one date filter and the fix (`<` to `<=`), cited S1 and S2, and the five sources matched the 4.5 results. I searched the passages and every claim is supported. One small point: the last sentence cites only S1, but one detail is in S2.

**Problems:** the Genie tab failed with an `attachment_id` error because the app's preinstalled SDK was older than the one I tested. I pinned `databricks-sdk==0.149.0`, added a fallback and a test. Free Edition had also stopped the app, so I had to start it before Deploy appeared again.

**Limits:** one question per tab, one run. Answer time was not measured.

**Lesson:** pin your SDK version, and test each tab on its own, because one uncaught error shows up under every tab.

## Scenario 3: Model-serving integration

Folder: `Scenarios/Scenario_3_Model_Serving_Integration/`

**Task:** call a model-serving endpoint from the app and handle a failure or timeout gracefully.

**What I did:** the runbooks tab now searches first and calls the model second, waits at most 45 seconds, turns each kind of error into a plain message, and falls back to the top 3 passages if the model fails. The technical error sits in a collapsed box. A test box in the tab lets me force a wrong endpoint name or a 1-second time limit. Offline tests: `test_helpers.py` (23) and `test_failure_paths.py`.

**Result (live):**

| Run | What the page showed |
|---|---|
| Normal | Cited answer with sources |
| Wrong endpoint name | "The AI model service could not be found..." plus the passages (the real error was `NotFound`) |
| 1-second limit | "The AI model service took too long to answer..." plus the passages |

**Problems:** the first passage showed as a huge heading because its text starts with a markdown `#`. I fixed it in `app.py` after the screenshots (plain text), so the fix is live from the next deploy.

**Limits:** only two failures were produced live. Permission, busy and unavailable are covered by tests only. The test box would be removed in a real deployment.

**Lesson:** separate search from generation, put a time limit on every model call, and map errors by class, not by message text.

## Scenario 4: Access control test

Folder: `Scenarios/Scenario_4_Access_Control_Test/`

**Task:** show that two users with different Unity Catalog permissions see different data in the same app, because of Unity Catalog and not the app's own logic.

**What I did:** a fourth tab runs the same query twice, once with the signed-in user's token ("As you") and once as the app's own identity ("As the app"). The row filter from Module 2.3 decides the rows. The app has no region names or conditions in it. Files: `app.py`, `helpers.py`, `01_row_filter_steps.sql`, three test files.

**Result (live):**

| Identity | As you | As the app |
|---|---|---|
| West user | West, 37 rows, 12,463.04 | no rows |
| East user | East, 31 rows, 9,893.50 | no rows |

12,463.04 + 9,893.50 = 22,356.54, which is the full total, so rows were hidden, not lost.

**Problems:** the first attempt gave a 403 for the user's own query while the app's query worked. Signing in again in a new private window fixed it. The probable cause is an old session whose token did not have the new `sql` scope (not proven). The second user also could not see the app, because the Apps list was filtered to apps they created.

**Limits:** two users, one run each. The "As the app" view was not tested with the filter off.

**Lesson:** put access control in Unity Catalog and pass the user's identity through, so the app has nothing to get wrong. Sign in again after adding a scope.

## Scenario 5: Live iteration

Folder: `Scenarios/Scenario_5_Live_Iteration/`

**Task:** make three small changes one at a time, redeploying and checking after each.

**What I did:** three releases on the Recon tab, each in its own folder with the full app, tests, screenshots and `VALIDATION_NOTES.md`:

| Release | Change | Live check |
|---|---|---|
| 1 (`release_1_status_filter/`) | Status filter (All, MATCH, MISMATCH) | 13, 12 and 1 rows; the one mismatch is RECON-0009 |
| 2 (`release_2_chart/`) | Bar chart of differing rows | One bar of height 3 at RECON-0009; none for MATCH |
| 3 (`release_3_csv_export/`) | CSV download button | Button shows 13, 12 and 1 row |

**Problems:** after release 1 two older tests failed because they picked the first radio button, which is now the new filter. I made the tests pick by label. The old test data had no `status` column, so I fixed the data and the tab now shows a message instead of a traceback.

**Limits:** I did not open the downloaded CSV live; its content is proven only by offline tests. Each release was checked once, in one browser.

**Commits at push:** one commit per release folder, in order (release 1 with the shared `app.yaml` and `requirements.txt`, then release 2, then release 3 with this README).

**Lesson:** one change per release makes a failure easy to place. Find page elements by label, not by position.

## AI use

I used an AI assistant to help write the app code, tests and this README, and I reviewed them. The deploys, grants, live runs and screenshots are mine. For scenario 1, three app files were already in the folder when I started it, so I reviewed them line by line and fixed one bug. The answers in the screenshots come from Genie and the Llama model, and I checked them against the answer key and the documents. All data is synthetic, and emails are blacked out in the screenshots.
