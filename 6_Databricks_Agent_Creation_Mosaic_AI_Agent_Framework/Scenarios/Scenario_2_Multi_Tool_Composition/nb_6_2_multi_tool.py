# Databricks notebook source
# MAGIC %md
# MAGIC # Scenario 6.2: multi-tool composition (the hero question)
# MAGIC Three tools: `get_recon_status` (Unity Catalog function), `search_runbooks` (Vector Search index), `ask_genie` (Genie space).
# MAGIC Four questions: one for each tool alone, and the hero question that needs the data **and** the runbook.
# MAGIC
# MAGIC Genie shows only one region per user while the 2.3 row filter is on: run `03_rollback.sql` from Scenario 2.3 first if you want both regions.

# COMMAND ----------

# MAGIC %pip install --upgrade -q "databricks-openai" "unitycatalog-ai[databricks]" "mlflow[databricks]>=3.1" "databricks-sdk>=0.149.0"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os, sys
sys.path.append(os.getcwd())
import pandas as pd
import fizzco_agent as fa

fa.enable_tracing()
space_id, title = fa.find_genie_space("Retail Sales")      # stops with a clear message unless exactly one space matches
fa.CFG["genie_space_id"] = space_id
print("Genie space:", title)
print("index      :", fa.CFG["index_name"], "| top_k:", fa.CFG["top_k"])

# COMMAND ----------

QUESTIONS = [
    ("recon only",   "What was the reconciliation status of the sell_out feed on 31 March 2026?",                                ["get_recon_status"]),
    ("runbook only", "The inventory pipeline failed only at the archive step. Do I need to rerun the whole pipeline?",          ["search_runbooks"]),
    ("genie only",   "What were net sell-in sales by region?",                                                                  ["ask_genie"]),
    ("both (hero)",  "Why did sell_in fail on 31 March and what do I do?",                                                      ["get_recon_status", "search_runbooks"]),
]
rows, full = [], {}
for label, q, needed in QUESTIONS:
    r = fa.run_agent(q)
    called = sorted(set(fa.tool_names(r)))
    full[label] = r
    rows.append({"case": label, "needed": ", ".join(needed), "called": ", ".join(called) or "none",
                 "needed_tools_used": all(t in called for t in needed), "question": q, "answer": r["answer"]})
table = pd.DataFrame(rows)
display(table[["case", "needed", "called", "needed_tools_used", "question"]])
print("cases where the needed tools were used:", int(table["needed_tools_used"].sum()), "of", len(table))

# COMMAND ----------

# MAGIC %md
# MAGIC ## The answers in full

# COMMAND ----------

for label, r in full.items():
    print("=" * 100); print(label.upper()); print("tools:", [(c["name"], c["arguments"]) for c in r["tool_calls"]]); print(); print(r["answer"])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check the hero answer against the sources (by eye)
# MAGIC The hero answer should contain: sell_in on 2026-03-31 was a MISMATCH (JOB-0049, RECON-0009: 63 source rows, 60 trusted, 3 difference), the cause (the end date was excluded by the date filter), the fix (make the end date inclusive, `<=`), and the rerun (RECON-0013, MATCH 63/63), with a citation such as `[RB-SELL-IN-001#c2]` or `[INC-2026-03-31-001#c1]`.
# MAGIC Screenshot the table above and the hero answer.
