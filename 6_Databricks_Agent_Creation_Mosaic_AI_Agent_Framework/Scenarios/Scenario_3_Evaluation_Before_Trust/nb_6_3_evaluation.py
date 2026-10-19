# Databricks notebook source
# MAGIC %md
# MAGIC # Scenario 6.3: evaluation before trust
# MAGIC Runs the 12-question `eval_set.csv` through `mlflow.genai.evaluate` with two code-based scorers:
# MAGIC `contains_expected_facts` (the answer holds the expected facts) and `uses_the_right_tools` (read from the trace).
# MAGIC An optional LLM judge is tried at the end. Put `eval_set.csv` in the same workspace folder as this notebook.

# COMMAND ----------

# MAGIC %pip install --upgrade -q "databricks-openai" "unitycatalog-ai[databricks]" "mlflow[databricks]>=3.1" "databricks-sdk>=0.149.0"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os, sys
sys.path.append(os.getcwd())
import mlflow, pandas as pd
import fizzco_agent as fa, fizzco_eval as fe

fa.enable_tracing()
fa.CFG["genie_space_id"], _title = fa.find_genie_space("Retail Sales")
rows = fe.load_eval_rows(os.path.join(os.getcwd(), "eval_set.csv"))
dataset = fe.to_dataset(rows)
print(len(dataset), "questions:", pd.Series([r["kind"] for r in rows]).value_counts().to_dict())

# COMMAND ----------

results = mlflow.genai.evaluate(
    data=dataset,
    predict_fn=lambda question: fa.ask(question),
    scorers=[fe.contains_expected_facts, fe.uses_the_right_tools],
)
print(results.metrics)

# COMMAND ----------

table = results.tables["eval_results"].copy()
table["case"] = table["case_id/value"]
table["kind"] = table["kind/value"]
table["facts_ok"] = table["contains_expected_facts/value"]
table["tools_ok"] = table["uses_the_right_tools/value"]
table["question"] = table["request"].astype(str).str.slice(0, 90)
table["answer"] = table["response"].astype(str).str.slice(0, 220)
summary = table[["case", "kind", "facts_ok", "tools_ok", "question", "answer"]]
display(summary)
print("facts ok:", int((table["facts_ok"].astype(str).isin(["True", "yes"])).sum()), "of", len(table))
print("tools ok:", int((table["tools_ok"].astype(str).isin(["True", "yes"])).sum()), "of", len(table))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Failures (document at least one)
# MAGIC For each failure: the question, what the agent answered, which scorer failed and why (the rationale), and the trace.

# COMMAND ----------

bad = table[~(table["facts_ok"].astype(str).isin(["True", "yes"]) & table["tools_ok"].astype(str).isin(["True", "yes"]))]
for _, r in bad.iterrows():
    print("=" * 100)
    print(r["case"], "|", r["kind"])
    print("QUESTION :", r["question"])
    print("ANSWER   :", r["answer"])
    print("FACTS    :", r["facts_ok"], "|", r["contains_expected_facts/rationale"])
    print("TOOLS    :", r["tools_ok"], "|", r["uses_the_right_tools/rationale"])
    print("TRACE ID :", r["trace_id"])
print()
print(len(bad), "of", len(table), "questions failed at least one scorer")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Optional: LLM judge (may not be available on Free Edition)
# MAGIC Skip this cell if it errors, and say so in the README. It asks a judge model whether each answer states the expected facts.

# COMMAND ----------

try:
    from mlflow.genai.scorers import Correctness
    judged = mlflow.genai.evaluate(
        data=fe.to_dataset(rows, with_judge_facts=True),
        predict_fn=lambda question: fa.ask(question),
        scorers=[Correctness()],
    )
    print(judged.metrics)
except Exception as exc:      # noqa: BLE001 - the judge is optional
    print("LLM judge not available here:", type(exc).__name__, str(exc)[:300])
