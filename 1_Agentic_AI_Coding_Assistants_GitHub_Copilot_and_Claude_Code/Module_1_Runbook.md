# Module 1 Runbook: Agentic AI Coding Assistants

How to complete the 6 scenarios using the synthetic **Fizzco  Data Lake** starter kit.
All data, names and systems here are fictional. Do not add real client or Tiger material.

> Before you start: confirm GitHub Copilot is Tiger-approved. Feature names and folder conventions change between VS Code versions, so where this runbook says "check", verify against the current Copilot docs.

## 0. One-time setup

| Step | Action |
|---|---|
| 1 | Open the `Assignment` folder in VS Code (File > Open Folder). Copilot files such as `.github/` must live at this root. |
| 2 | Open Copilot Chat and switch to **Agent** mode |
| 3 | Run once in a terminal from the `Assignment` folder: `cd shared/fizzco_lake && python3 generate_synthetic_data.py`. Run all scripts from inside `fizzco_lake`, because paths are relative. (data already generated; this proves it is reproducible) |
| 4 | Create `evidence/` with one subfolder per scenario: `s1_1` ... `s1_6` |
| 5 | Start `module_1/README.md` (template at the end of this file) |

For every scenario, save: the prompt you used, a screenshot of the result, and a one-paragraph lesson.

## What is in the starter kit

| Path | What it is | Used in |
|---|---|---|
| `shared/fizzco_lake/adf/*.json` | 3 pipeline definitions (sell_in, inventory, promo) | 1.1, 1.2 |
| `shared/fizzco_lake/databricks/*.py` | 3 transform notebooks, `config.py`, `recon_utility.py` | 1.2, 1.4, 1.5 |
| `shared/fizzco_lake/ddl/*.sql` | 3 table definitions | 1.2 |
| `shared/fizzco_lake/data/raw` and `trusted` | Small synthetic CSVs | 1.5, 1.6 |
| `shared/inventory/App_Object_Inventory_FILLED.csv` | Object inventory with 2 deliberate errors | 1.3 |
| `shared/inventory/App_Object_Inventory_Template.csv` | Empty template | 1.3 |

The legacy code is intentionally untidy (mixed naming, `print`, a bare `except`). Scenario 1.4 is where you fix that with standards.

---

## Scenario 1.1 Repeatable workflow (prompt file)

**Goal:** a reusable `/document-pipeline` command that turns a pipeline JSON into a lineage document. Run it on two different pipelines.

**Step 1.** Ask Copilot to create the prompt file:

```text
Create a reusable prompt file at .github/prompts/document-pipeline.prompt.md for agent mode.
Input: the path of an ADF pipeline JSON (parameter).
Output: a Markdown lineage document saved to shared/fizzco_lake/docs/Pipeline_<pipeline_name>.md with these sections:
1. Purpose (one line from the description field)
2. Parameters (table)
3. Activity flow (table: order, activity name, type, depends on, source, target)
4. Lineage (source -> raw -> trusted, with container and folder)
5. Notebook used (path and parameters passed)
6. Risks or observations (hard-coded values, missing error handling)
Rules: only use facts present in the JSON. If something is not in the file write "Not specified". Do not invent table or column names.
```

**Step 2.** Run it twice: `/document-pipeline shared/fizzco_lake/adf/pl_fizzco_sell_in_load.json`, then the same for `pl_fizzco_inventory_load.json`.

**Step 3 (verify).** Open both generated docs. Check that the inventory doc mentions the archive step and the `fizzco-raw-archive` container, and the sell_in doc does not.

**Done when:** one prompt file, two generated docs, two screenshots. Note the difference between the two outputs as proof of reuse.

---

## Scenario 1.2 Subagents for context management

**Goal:** investigate with a read-only subagent, then edit only the files it lists.

**Task:** rename the container `fizzco-raw` to `fizzco-landing`. Trap: `fizzco-raw-archive` is a *different* container and must stay unchanged.

**Prompt:**

```text
Use a subagent (runSubagent) for investigation. The subagent must be read-only and must NOT edit any file.
Task for the subagent: find every occurrence of the exact container name "fizzco-raw" in this workspace (ADF JSON, Python notebooks, DDL SQL, docs). Exclude "fizzco-raw-archive", which is a different container. Return ONLY a compact table: file path, line number, the matching text.
Then, in the main session, use only that table to rename "fizzco-raw" to "fizzco-landing". Show me the table before you edit.
After editing, verify: search the workspace again and confirm zero "fizzco-raw" matches except "fizzco-raw-archive", and run: cd shared/fizzco_lake && python3 databricks/promo_transform.py
```

If your Copilot version does not expose a subagent tool, check the docs for how to enable it, or run this scenario in Claude Code with its subagent (Task) feature and say so in your write-up.

**Expected:** exactly 11 matches in 8 files (6 in the 3 ADF JSON files, `config.py`, 3 DDL files, and a hard-coded URI in `inventory_transform.py` that the subagent should catch). One extra hit, `fizzco-raw-archive` in `pl_fizzco_inventory_load.json`, must be left alone.

**Done when:** you have the subagent's returned table, the git diff, and a search proving nothing was missed.

---

## Scenario 1.3 Packaging a skill

**Goal:** a skill that validates an app object inventory, picked up automatically.

**Step 1.** Prompt:

```text
Create a skill for validating an App Object Inventory CSV, as SKILL.md plus a helper script validate_inventory.py.
SKILL.md needs: a description that says WHEN to use it (user asks to check, validate or review an inventory, object list or lineage sheet), and step-by-step instructions.
Rules the validator must check against shared/inventory/App_Object_Inventory_Template.csv columns:
1. All required columns present, in template order.
2. object_id unique.
3. Every depends_on value (if not empty) exists as an object_id.
4. object_type is one of Pipeline, Notebook, Table.
5. status is Active or Retired.
Output a table of violations with row number and rule, and a final PASS or FAIL.
Place the skill where this Copilot version loads skills (check the current Copilot docs; commonly .github/skills/<name>/SKILL.md).
```

**Step 2 (the test that counts).** Open a **new chat** and say: *"Can you check the inventory sheet in the shared/inventory folder for problems?"* Do not name the skill.

**Expected result:** the validator flags exactly 2 problems:

| Row | Problem |
|---|---|
| OBJ-005 appears twice | Duplicate `object_id` |
| `OBJ-099` | `depends_on` points to an object that does not exist |

If the skill is not picked up, tighten the description (add trigger phrases) and retest. Record both attempts.

**Done when:** SKILL.md, the script, and a screenshot of the new chat using it.

---

## Scenario 1.4 Enforcing standards automatically

**Goal:** an instructions file with 3 conventions, followed without reminders.

**Step 1.** Create `.github/copilot-instructions.md` (you can start from Part B of your COPILOT_MASTER_GUIDE) with exactly these three conventions:

| # | Convention | Rule |
|---|---|---|
| 1 | Naming | snake_case for functions, variables and files; tables prefixed `raw_` or `trusted_` |
| 2 | Error handling | no bare `except`; catch specific exceptions; error message includes the failing input |
| 3 | Logging | use the `logging` module (no `print`), format `%(asctime)s %(levelname)s %(name)s - %(message)s`, log start, row count and end |

**Step 2.** Two unrelated requests in fresh chats, with no mention of the conventions:

```text
Request A: Write a function that reads shared/fizzco_lake/data/raw/inventory.csv and returns the SKUs whose total stock_on_hand is below 1000.
```

```text
Request B: Write a Python script that generates a CREATE TABLE statement for a new table called trusted_returns with columns return_date, retailer_id, sku, units_returned, reason_code.
```

**Step 3 (audit).** Fill this table for each output:

| Convention | Request A | Request B |
|---|---|---|
| Naming | pass or fail | pass or fail |
| Error handling | pass or fail | pass or fail |
| Logging | pass or fail | pass or fail |

If any fail, tighten the instructions file and rerun. The legacy notebooks (`Transform`, `PromoTransform`, bare `except`) show what "before" looks like.

**Done when:** instructions file, two outputs, completed audit table.

---

## Scenario 1.5 Agentic loop discipline

**Goal:** the assistant diagnoses before editing, fixes, then verifies with a test.

**Prompt (bug report with no other context):**

```text
Bug report: "The reconciliation for sell_in says the trusted table is missing rows compared to raw, but nothing was lost in the pipeline."
Work in four stages and do not skip any:
(a) Reproduce and diagnose using tools (run the code, inspect the data). Show me your findings. Do NOT edit any file yet.
(b) Propose the fix and wait for my approval.
(c) After I say go, apply the fix.
(d) Verify: write a pytest test that fails before the fix and passes after, run it, and run: cd shared/fizzco_lake && python3 databricks/recon_utility.py again. Reject your own answer if the verify step is missing.
```

**What you should see:** `MISMATCH`, source 63 vs trusted 60. Root cause: `count_trusted_rows` uses `start <= d < end`, while `count_source_rows` uses `<=`. The 3 rows dated 2026-03-31 are excluded on one side only. The fix is making the comparison consistent.

**Done when:** diagnosis log, approval step, test that fails then passes, final run showing `MATCH`.

---

## Scenario 1.6 Live data grounding via MCP

**Goal:** the assistant answers a schema question from a connected MCP server, not from memory.

| Path | When | Setup |
|---|---|---|
| A. Databricks MCP | You have an approved Databricks workspace | Add the Databricks MCP server in VS Code (check current docs) and point it at your workspace using environment variables, never hard-coded tokens |
| B. Local fallback | No workspace yet | Load the synthetic CSVs into a local SQLite file and connect a local database MCP server (check current Copilot and MCP docs for the exact server and config) |

For path B, ask Copilot to create the SQLite file from the trusted CSVs first:

```text
Create a script load_sqlite.py that loads the three trusted CSVs from shared/fizzco_lake/data/trusted into a SQLite database fizzco.db, one table each, with correct column types. Verify by printing row counts.
```

**Test prompt:**

```text
What is the schema of the trusted_sell_in table, and how many rows does it have? Use the connected MCP database tool. Show me which tool you called. Do not answer from memory or from reading the CSV files.
```

**Pass criteria:** the chat shows an MCP tool call, and the schema and row count (63) match the data. Then ask a question the tool cannot answer ("what is the price of a Fizzco share?") and check it says it does not know.

**Done when:** a screenshot showing the tool call and output.

---

## Module README template (`module_1/README.md`)

| Section | Content |
|---|---|
| Overview | One paragraph: synthetic Fizzco lake, 6 scenarios, tools used |
| Compliance note | All data is synthetic; no client or Tiger data; AI use disclosed; outputs reviewed by a human |
| Scenario table | Scenario, deliverable path, evidence path, status |
| Per scenario | Goal, Prompt, Result, Verification, Lesson learned (3 to 5 lines each) |
| How to reproduce | Commands from step 0 |

## Suggested order and time

| Order | Scenario | Rough effort |
|---|---|---|
| 1 | 1.4 Standards (makes later outputs cleaner) | 30 min |
| 2 | 1.1 Prompt file | 30 min |
| 3 | 1.2 Subagent | 30 min |
| 4 | 1.5 Agentic loop | 30 min |
| 5 | 1.3 Skill | 45 min |
| 6 | 1.6 MCP | 45 to 60 min |

---

## Notes from execution

Corrections learned while running the scenarios. The steps above are kept as written; use these where they differ.

| Scenario | Note |
|---|---|
| 1.1 | `/document-pipeline` did not appear in the slash list as a prompt file in the tested Copilot session (VS Code 1.140.0, Copilot Chat 0.68.0), because prompt files are not loaded in Agent Host sessions. The same instructions were added as a skill at `.github/skills/document-pipeline/SKILL.md`, which does appear. Output files are named `lineage_<pipeline_name>.md` (snake_case). |
| 1.2 | After this scenario the container is `fizzco-landing`. Any mention of `fizzco-raw` in the steps above is the starting state. The subagent's line numbers were wrong for most rows, so edit by matching text, not by line number. The generated lineage docs in `shared/fizzco_lake/docs` predate the rename and are refreshed at the start of Module 3. |
| 1.4 | Run both requests in fresh chats with no file attached, and crop the screenshots so no attachment chip or chat title from another request is visible. |
| 1.5 | Run in stages with a human approval gate. The test lives at `shared/fizzco_lake/tests/test_recon_utility.py` and runs with `python3 -m unittest` when pytest is not installed. |
