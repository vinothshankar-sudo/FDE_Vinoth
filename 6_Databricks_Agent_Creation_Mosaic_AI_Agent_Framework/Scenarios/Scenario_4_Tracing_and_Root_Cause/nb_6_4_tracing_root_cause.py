# Databricks notebook source
# MAGIC %md
# MAGIC # Scenario 6.4: tracing and root cause
# MAGIC Break one tool on purpose (point the function at a stale copy of the recon table), watch the agent give a wrong answer, and find
# MAGIC the failing step from the **trace**, without reading the agent code. Then restore the tool.
# MAGIC The stale table is a synthetic snapshot taken before 31 March: it has no run for that day.

# COMMAND ----------

# MAGIC %pip install --upgrade -q "databricks-openai" "unitycatalog-ai[databricks]" "mlflow[databricks]>=3.1" "databricks-sdk>=0.149.0"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os, sys
sys.path.append(os.getcwd())
import mlflow, pandas as pd
import fizzco_agent as fa

fa.enable_tracing()
QUESTION = "What was the reconciliation status of sell_in on 31 March 2026?"

def ask_and_trace(question):
    r = fa.run_agent(question, enabled=["get_recon_status"])
    mlflow.flush_trace_async_logging()
    trace = mlflow.get_trace(mlflow.get_last_active_trace_id())
    return r, trace

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Baseline: the tool works
# MAGIC Expected: both runs, RECON-0009 MISMATCH and RECON-0013 MATCH.

# COMMAND ----------

good, good_trace = ask_and_trace(QUESTION)
print(good["answer"])
display(pd.DataFrame(fa.trace_summary(good_trace)))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Break the tool
# MAGIC Creates `workspace.fizzco.gold_recon_results_stale` (rows before 2026-03-31 only) and points the function at it.
# MAGIC Nothing else changes: the agent code, the model and the question are the same.

# COMMAND ----------

spark.sql("CREATE OR REPLACE TABLE workspace.fizzco.gold_recon_results_stale AS "
          "SELECT * FROM workspace.fizzco.gold_recon_results WHERE recon_date < DATE'2026-03-31'")
spark.sql(fa.recon_function_sql("workspace.fizzco.gold_recon_results_stale"))
print("tool broken: the function now reads gold_recon_results_stale")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Ask again: the final answer is wrong

# COMMAND ----------

bad, bad_trace = ask_and_trace(QUESTION)
print(bad["answer"])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Find the failing step from the trace
# MAGIC Read the table top to bottom: the first step whose **output** is already wrong is the root cause. Screenshot this table and the trace view.

# COMMAND ----------

display(pd.DataFrame(fa.trace_summary(bad_trace)))

# COMMAND ----------

# MAGIC %md
# MAGIC Write the root-cause note from what the trace shows. Template:
# MAGIC * **Wrong final answer:** what the agent said.
# MAGIC * **Step that went wrong:** the span name, its input (were the arguments right?) and its output (what did the tool return?).
# MAGIC * **Why that step:** the model's request was right, the tool's answer was already wrong, so the fault is in the tool or its data, not in the model or the prompt.
# MAGIC * **How it was confirmed:** run the function by hand and compare with the real table.
# MAGIC * **Fix:** restore the function (next cells).

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Restore the tool and prove it

# COMMAND ----------

spark.sql(fa.recon_function_sql())
spark.sql("DROP TABLE IF EXISTS workspace.fizzco.gold_recon_results_stale")
fixed, fixed_trace = ask_and_trace(QUESTION)
print(fixed["answer"])
display(pd.DataFrame(fa.trace_summary(fixed_trace)))
