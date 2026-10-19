# Module 1: Agentic AI Coding Assistants 

Agentic coding assistants do more than autocomplete. They read a codebase, plan a multi-step change, use tools (terminal, file edits, search), check the result and repeat until the task is done. This module uses GitHub Copilot (agent mode in VS Code) on the Fizzco lake code to try the building blocks: prompt files, subagents, skills, instructions files, staged work with approval, and MCP.

## Scenarios

| # | Scenario | Status |
|---|---|---|
| 1 | [Repeatable workflow](#scenario-1-repeatable-workflow) | Done |
| 2 | [Context management with subagents](#scenario-2-context-management-with-subagents) | Done |
| 3 | [Packaging a skill](#scenario-3-packaging-a-skill) | Done |
| 4 | [Enforcing standards automatically](#scenario-4-enforcing-standards-automatically) | Done |
| 5 | [Agentic loop discipline](#scenario-5-agentic-loop-discipline) | Done |
| 6 | [Live data grounding via MCP](#scenario-6-live-data-grounding-via-mcp) | Done |

Each scenario folder under `Scenarios/` has the files that were made and an `evidence/` folder with screenshots. The live copies of the prompt, skill and instructions files are in `.github/`. `Module_1_Runbook.md` has the step-by-step runbook I followed.

## Scenario 1: Repeatable workflow

Folder: `Scenarios/Scenario_1_Repeatable_Workflow_Prompt_File/`

**Task:** build a slash command or prompt file for a weekly manual task and run it on two different inputs.

**What I did:** the weekly task is "write up what an ADF pipeline does and where its data goes". I made `/document-pipeline <pipeline JSON>`, which writes a lineage document with six fixed sections (purpose, parameters, activity flow, lineage, notebook, risks). Rule: use only facts in the JSON, otherwise write "Not specified". I ran it on the sell_in and the inventory pipelines (`lineage_pl_fizzco_sell_in_load.md`, `lineage_pl_fizzco_inventory_load.md`).

**Result:** the sell_in document has 2 activities and no archive step. The inventory one has 3 activities, including an archive step into `fizzco-raw-archive`. Same command and structure, different content driven only by the input. I checked both against the JSON line by line, and nothing was invented.

**Problems:** the prompt file did not show up in the slash list of my Copilot session (VS Code 1.140.0), and the docs say prompt files are not loaded in some session types. I kept the prompt file (`document-pipeline.prompt.md`) and also packaged the same instructions as a skill (`skill_version/`), which is the version I ran. In run 2 Copilot said it did not re-read the saved file, so the built-in verify step is not guaranteed.

**Lesson:** a reusable command keeps the structure identical, so documents are easy to compare. Check the command appears in the slash list before relying on it.

## Scenario 2: Context management with subagents

Folder: `Scenarios/Scenario_2_Context_Management_Subagents/`

**Task:** delegate an investigation to a subagent and bring back only the file list.

**What I did:** renamed the storage container `fizzco-raw` to `fizzco-landing` in the lake code. A read-only subagent found every occurrence, then the main session edited only those files. The trap: `fizzco-raw-archive` is a different container and must stay.

**Result:** the subagent found 11 matches in 8 files in 28 seconds and edited nothing. 11 occurrences were renamed in 8 files, and the archive container, the storage account and the dataset names were left alone. A search finds zero old-name matches, and `promo_transform.py` now prints `container: fizzco-landing rows: 12`. I proved only the 8 expected files changed with `diff` against a backup (`rename_diff.patch`, `zero_stale_search.txt`, `subagent_returned_file_list.md`).

**Problems:** 9 of the subagent's 11 line numbers were wrong, so I told the main session to match on text, not line number. The main session also said it could not see the subagent's table and chose the files itself. The result matches the subagent's list, but this run does not prove it used only that list.

**Lesson:** trust a subagent's list, but check its details.

## Scenario 3: Packaging a skill

Folder: `Scenarios/Scenario_3_Packaging_a_Skill/`

**Task:** turn a process into a `SKILL.md` and check the assistant picks it up from plain English without the skill being named.

**What I did:** a `validate-inventory` skill (`SKILL.md`) plus a validator script (`validate_inventory.py`, standard library only) that checks 5 rules on the object inventory: columns match the template, `object_id` unique, `depends_on` exists, `object_type` valid, `status` valid.

**Result:** in a new chat I asked only: "Can you check the inventory sheet in the inventory folder for problems?" Copilot found the file, ran the validator, showed the table and FAIL, and did not edit the file. It found 2 violations: a duplicate `OBJ-005` (line 7) and a missing dependency `OBJ-099` (line 9), which matches my own answer key. No retries were needed. I also ran my own tests (`validator_verification_runs.txt`): repaired file gives PASS, bad types give 4 violations, a swapped header is reported, missing file gives exit code 2.

**Limits:** one `depends_on` per row. Screenshot `04_auto_trigger_steps_expanded.png` is not captured (optional). Copilot used `sys.stdout.write` instead of `print` because the instructions forbid `print`. I accepted that.

**Lesson:** the `description` line is the trigger. Keep the rules in a script so the result is the same every time.

## Scenario 4: Enforcing standards automatically

Folder: `Scenarios/Scenario_4_Enforcing_Standards_Automatically/`

**Task:** write an instructions file with 3 team conventions and check Copilot follows them in two unrelated requests without reminders.

**What I did:** `.github/copilot-instructions.md` (copy: `copilot-instructions.md`) encodes: naming (snake_case, UPPER_SNAKE_CASE constants, `raw_` or `trusted_` table prefix), error handling (no bare `except`, specific exceptions, include the failing input), and logging (`logging` module with a fixed format, no `print`, log start, row count and end). Request A: "read inventory.csv and return SKUs with stock below 1000". Request B: "write a script that generates a CREATE TABLE for `trusted_returns`". The conventions were not mentioned in either prompt.

**Result:** both requests followed all three conventions (audit table checked by hand). Request A is `request_a_low_stock.py`. Request B is `request_b_generate_trusted_returns_ddl.py` with its output `request_b_output_trusted_returns.sql`.

**Problems:** my first Request B run happened in the same chat as A, so it could have been influenced. I reran it in a fresh chat. The code differed but still passed 3 of 3, and the first run's files are kept outside the submission folder. The audit also found that Request A skips the `end` log when an error is raised (a `finally` block would fix it).

**Lesson:** write the rules once instead of repeating them in every prompt. Test in a fresh chat.

## Scenario 5: Agentic loop discipline

Folder: `Scenarios/Scenario_5_Agentic_Loop_Discipline/`

**Task:** give the assistant a bug report and make it diagnose before editing, propose a fix, apply it, and verify. Reject any answer that skips verification.

**What I did:** the bug report was "reconciliation for sell_in says the trusted table is missing rows, but nothing was lost". I asked for stages with a stop for my approval after the proposal. I approved with changes: minimal fix only, a test on the real data, and say which test runner.

**Result:** Copilot reproduced source 63 vs trusted 60 (MISMATCH) and found both tables hold 63 rows. The two counting functions treat the end date differently, so the 3 rows dated 31 March were the whole difference. The fix is one character (`<` to `<=` in `count_trusted_rows`, `recon_utility_fix.patch`). The test fails before the fix (3 of 4) and passes after (4 of 4), and the reconciliation now shows MATCH 63 and 63 with exit code 0. A test also proves real row loss is still caught (`diagnosis_log.md`, `test_recon_utility.py`, `test_and_recon_runs.txt`).

**Limits:** Copilot summarised the last stages in one message, so the "fails before" output is in `test_and_recon_runs.txt` (I reproduced it from a backup), not in a separate screenshot. Copilot noticed other problems in `sell_in_transform.py` and left them alone on purpose.

**Lesson:** an approval gate kept the fix small and added a real-data test. A test written before the fix proves the bug existed.

## Scenario 6: Live data grounding via MCP

Folder: `Scenarios/Scenario_6_Live_Data_Grounding_via_MCP/`

**Task:** ask a question that needs real data and confirm the assistant uses the connected MCP server, not memory.

**What I did:** Databricks access was not confirmed yet, so I used a local path. `load_sqlite.py` loads the 3 trusted CSVs into SQLite, and a read-only SQLite MCP server (`mcp-sqlite-server`, version pinned, config in `mcp.json`, no secrets) is connected to Copilot.

**Result:** I asked for the schema and row count of `trusted_sell_in`. Copilot asked permission to call `fizzco-sqlite: table_info`, named the tool and arguments it called, and answered 63 rows and 7 columns, which matches my own check (`mcp_verification.txt`). When asked for a Fizzco share price it declined and said it would be inventing a number.

**Problems:** the server exited silently on my Mac because Node 26.5.0 has no prebuilt SQLite binary. I pinned the server to Node 22 with `npx -p node@22`, and the same package then returned all five tools. The exact error on my Mac may differ from the one I reproduced elsewhere, but the cause is the same.

**Limits:** a local database, not Databricks. `05_mcp_tools_listed.png` is not captured (optional). The "no share-price data" sentence rests on the earlier `table_info` result in the same chat.

**Lesson:** an MCP answer is only grounded if the tool call is visible. Pin the runtime as well as the package, and test the "cannot answer" case.

## Appendix: prompts used

These are the prompts I gave Copilot (agent mode), copied from my original scenario notes.

### Scenario 1: Repeatable workflow

```text
Create a reusable prompt file at .github/prompts/document-pipeline.prompt.md for agent mode.
Input: the path of an ADF pipeline JSON (a parameter the user passes after the command).
Output: a Markdown lineage document saved to shared/fizzco_lake/docs/lineage_<pipeline_name>.md with these sections:
1. Purpose (one line from the description field)
2. Parameters (table)
3. Activity flow (table: order, activity name, type, depends on, source, target)
4. Lineage (source -> raw -> trusted, with container and folder)
5. Notebook used (path and parameters passed)
6. Risks or observations (hard-coded values, missing error handling)
Rules: only use facts present in the JSON. If something is not in the file write "Not specified". Do not invent table or column names. Mark the document as AI-generated and synthetic at the top. Do not run it yet; just create the prompt file and tell me how to invoke it.
```

Runs (each in a new chat, Agent mode):

```text
/document-pipeline shared/fizzco_lake/adf/pl_fizzco_sell_in_load.json
/document-pipeline shared/fizzco_lake/adf/pl_fizzco_inventory_load.json
```

### Scenario 2: Context management with subagents

Step 1, investigate only (new chat, Agent mode):

```text
Use a subagent (runSubagent) for investigation. The subagent must be read-only and must NOT edit any file.
Task for the subagent: find every occurrence of the exact container name "fizzco-raw" under shared/fizzco_lake (ADF JSON, Python notebooks, DDL SQL). Do not search the docs folder. Exclude "fizzco-raw-archive", which is a different container. Return ONLY a compact table: file path, line number, the matching text.
In the main session, show me that table and then STOP. Do not edit anything until I say go.
```

Step 2, after human review of the table:

```text
Go. Use only the file list from the subagent's table to decide which files to edit, and edit exactly those 8 files. Do NOT trust the line numbers in the table, because most are wrong (they were counted across files). Find each occurrence by its matching text inside the file instead.
Rename the exact container name "fizzco-raw" to "fizzco-landing" in those files. Do not touch "fizzco-raw-archive", the storage account "fizzcostorage", dataset names such as ds_adls_fizzco_raw_*, or any folder names such as raw/.
Do not edit anything under shared/fizzco_lake/docs.
After editing, verify and show me the results:
1. Search under shared/fizzco_lake (excluding docs) and confirm zero "fizzco-raw" matches except "fizzco-raw-archive".
2. Run: cd shared/fizzco_lake && python3 databricks/promo_transform.py
3. List every file you changed.
```

### Scenario 3: Packaging a skill

Fresh Agent-mode chat, nothing attached. The prompt did not reveal which errors exist in the inventory.

```text
Follow .github/copilot-instructions.md for everything you create.

Create an Agent Skill that validates our application object inventory before cutover.

Files to create:
1. .github/skills/validate-inventory/SKILL.md
2. .github/skills/validate-inventory/validate_inventory.py

Validator (validate_inventory.py), Python standard library only:
- Takes the path of an inventory CSV as a command-line argument.
- Reads the expected column names and order from shared/inventory/App_Object_Inventory_Template.csv at runtime. Do not hard-code the column list.
- Checks these 5 rules:
  R1. All template columns are present, in template order.
  R2. object_id is unique.
  R3. Every non-empty depends_on value exists as an object_id in the same file.
  R4. object_type is one of: Pipeline, Notebook, Table.
  R5. status is one of: Active, Retired.
- Prints a Markdown table of violations with columns: file line number (header is line 1), object_id, rule, detail. Then prints a final line: PASS or FAIL.
- Exit code 0 on PASS, 1 on FAIL, 2 if the file cannot be read.
- Follow our standards: specific exceptions with the failing input in the message, logging instead of print for diagnostics, constants in UPPER_SNAKE_CASE.

Skill (SKILL.md):
- Frontmatter: name must be validate-inventory (matches the folder), plus a description that says WHEN to use it. It must trigger when a user asks to check, validate, review or audit an inventory, object list, object register or lineage sheet, including casual phrasing such as "check the inventory for problems".
- Body: clear step-by-step instructions: (1) locate the inventory CSV, asking only if there is more than one candidate; (2) run the validator script; (3) show the violations table and the PASS or FAIL result exactly as printed; (4) never edit the inventory file, and only propose fixes if the user asks.

Do not run the validator against any file yet. Show me the two files when done.
```

Auto-trigger test (a second, new chat; the skill is not named):

```text
Can you check the inventory sheet in the inventory folder for problems?
```

### Scenario 4: Enforcing standards automatically

Request A:

```text
Write a function that reads shared/fizzco_lake/data/raw/inventory.csv and returns the SKUs whose total stock_on_hand is below 1000.
```

Request B:

```text
Write a Python script that generates a CREATE TABLE statement for a new table called trusted_returns with columns return_date, retailer_id, sku, units_returned, reason_code.
```

### Scenario 5: Agentic loop discipline

Stage 1 (new chat, Agent mode, nothing attached):

```text
Bug report: "The reconciliation for sell_in says the trusted table is missing rows compared to raw, but nothing was lost in the pipeline."
Work in stages and do not skip any:
(a) Reproduce and diagnose using tools (run the code, inspect the data). Run: cd shared/fizzco_lake && python3 databricks/recon_utility.py. Show me your findings and the evidence. Do NOT edit or create any file in this stage.
(b) Propose the fix, and the test you would write, then STOP and wait for me to say go.
(c) Only after I say go: first create the test and run it to show it FAILS on the current code. Then apply the fix.
(d) Verify: run the test again and show it PASSES, then run python3 databricks/recon_utility.py again. If the verify step is missing, I will reject your answer.
Start with stage (a) and (b) only. Do not continue to (c) until I reply.
```

Approval (same chat):

```text
go. Approved with these changes:
1. Minimal fix only: change "<" to "<=" in count_trusted_rows. Do NOT add the shared helper or refactor anything else.
2. Put the test at shared/fizzco_lake/tests/test_recon_utility.py and run it from shared/fizzco_lake.
3. Add one more test that runs reconcile() on the real files data/raw/sell_in.csv and data/trusted/trusted_sell_in.csv for 2026-01-01 to 2026-03-31 and expects MATCH with source and trusted both 63. Do not hard-code 60 anywhere.
4. Use pytest if it is installed, otherwise python3 -m unittest, and tell me which you used.
Do not touch sell_in_transform.py or any data file.
Order: (c1) create the test only, run it, and show me it FAILS on the current code. (c2) then apply the fix. (d) run the test again to show it PASSES, then run python3 databricks/recon_utility.py from shared/fizzco_lake and show MATCH with exit code 0.
```

### Scenario 6: Live data grounding via MCP

Step 1, loader (fresh Agent-mode chat):

```text
Follow .github/copilot-instructions.md for everything you create.

Create shared/fizzco_lake/load_sqlite.py. It loads the three trusted CSVs from shared/fizzco_lake/data/trusted (trusted_sell_in, trusted_inventory, trusted_promo) into a SQLite database shared/fizzco_lake/fizzco.db, one table each, named after the CSV file, with correct column types (dates as TEXT in ISO format, units and stock as INTEGER, amounts as REAL, ids and SKUs as TEXT). Python standard library only. Drop and recreate each table so the script is safe to re-run. Use logging, not print, and log the row count of each table at the end. Do not edit any existing file.
Then run it once and show me the row counts.
```

Step 2, test prompt (new Agent-mode chat):

```text
The database is shared/fizzco_lake/fizzco.db. What is the schema of the trusted_sell_in table, and how many rows does it have? Use the connected MCP database tool. Show me which tool you called. Do not answer from memory or from reading the CSV files.
```

Step 3, out-of-scope question (same chat):

```text
What is the price of a Fizzco share?
```

## AI use

This whole module is about using AI coding assistants, so AI use is the point. GitHub Copilot produced the prompt and skill outputs, the validator, the test, the fix and the loader, and I reviewed each result against the source files and my own checks. All data is synthetic. No credentials are in any file.
