# Databricks notebook source
# MAGIC %md
# MAGIC # Scenario 6.1: first tool-calling agent
# MAGIC Fizzco Migration Assurance Hub (synthetic data). One Unity Catalog function, `get_recon_status(feed, recon_date)`, is the tool.
# MAGIC The model decides when to call it and when to answer directly.
# MAGIC
# MAGIC **Before you run:** this notebook, `fizzco_agent.py` and the other module-6 files must be in the same workspace folder. Use **Serverless** compute.

# COMMAND ----------

# MAGIC %pip install --upgrade -q "databricks-openai" "unitycatalog-ai[databricks]" "mlflow[databricks]>=3.1" "databricks-sdk>=0.149.0"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os, sys
sys.path.append(os.getcwd())          # the folder that holds fizzco_agent.py
import pandas as pd
import fizzco_agent as fa

fa.enable_tracing()                   # model calls are traced; tool calls and the agent are traced by the module
print("model endpoint:", fa.CFG["model_endpoint"])
print("tool function :", fa.CFG["function_name"])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: create the tool (Unity Catalog function)
# MAGIC The function text lives in `fizzco_agent.recon_function_sql()` (the same text is in `01_create_get_recon_status.sql`).

# COMMAND ----------

spark.sql(fa.recon_function_sql())
display(spark.sql("DESCRIBE FUNCTION EXTENDED workspace.fizzco.get_recon_status"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: call the tool by hand, the way the agent will
# MAGIC Expected for sell_in on 2026-03-31: **two lines**: `RECON-0009 ... MISMATCH (63, 60, 3)` and `RECON-0013 ... MATCH (63, 63, 0)`.

# COMMAND ----------

result = fa._uc_client().execute_function(fa.CFG["function_name"], {"feed": "sell_in", "recon_date": "2026-03-31"})
print("error:", result.error)
print(result.value)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: the agent decides: tool or direct answer
# MAGIC Only this one tool is offered in 6.1. Expect tools for the first two questions and none for the last two.

# COMMAND ----------

QUESTIONS = [
    ("tool",   "What was the reconciliation status of sell_in on 31 March 2026?"),
    ("tool",   "Did the promo feed reconcile on 28 February 2026?"),
    ("direct", "Hello! What can you help me with?"),
    ("direct", "What is 12 times 12?"),
]
rows = []
for expected, q in QUESTIONS:
    r = fa.run_agent(q, enabled=["get_recon_status"])
    called = fa.tool_names(r)
    rows.append({"expected": expected, "tools_called": ", ".join(called) or "none", "rounds": r["rounds"],
                 "as_expected": (bool(called) == (expected == "tool")), "question": q, "answer": r["answer"]})
table = pd.DataFrame(rows)
display(table)
print("tool-vs-direct decisions as expected:", int(table["as_expected"].sum()), "of", len(table))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: look at one trace
# MAGIC Open the trace shown under the cells above (or **Experiments** > this notebook's experiment > **Traces**). Screenshot a trace that shows the `get_recon_status` span with its inputs and output.
