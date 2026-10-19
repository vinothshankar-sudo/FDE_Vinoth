# Databricks notebook source
# MAGIC %md
# MAGIC # Scenario 6.5: deploy the agent to Model Serving and monitor it
# MAGIC Wraps the Fizzco agent for Model Serving, logs it with MLflow, registers it in Unity Catalog, deploys it, sends a few live
# MAGIC requests and shows how it is monitored (latency, error rate, a sample of logged interactions, traces).
# MAGIC
# MAGIC **Before you run:** this notebook, `fizzco_agent.py` and `fizzco_serving_agent.py` must be in the same workspace folder (`fizzco-agent`). Use **Serverless** compute.
# MAGIC Run one cell at a time. Deployment can take up to about 15 minutes. If a step fails, stop and send the error text: Free Edition may not allow every step, and the exact error is the evidence.

# COMMAND ----------

# MAGIC %pip install --upgrade -q "databricks-agents>=1.2.0" "mlflow[databricks]>=3.1.3" "databricks-openai" "unitycatalog-ai[databricks]" "databricks-sdk>=0.149.0"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os, sys, time, json
sys.path.append(os.getcwd())
import mlflow, pandas as pd
from databricks.sdk import WorkspaceClient
from mlflow.models.resources import (DatabricksFunction, DatabricksGenieSpace, DatabricksServingEndpoint,
                                     DatabricksSQLWarehouse, DatabricksVectorSearchIndex)
import fizzco_agent as fa

mlflow.set_registry_uri("databricks-uc")
w = WorkspaceClient()

UC_MODEL = "workspace.fizzco.fizzco_agent"
SPACE_ID, SPACE_TITLE = fa.find_genie_space("Promotions Analytics")      # stops unless exactly one space matches
fa.CFG["genie_space_id"] = SPACE_ID

warehouses = list(w.warehouses.list())
print("SQL warehouses:", [(x.name, x.id) for x in warehouses])
WAREHOUSE = next((x for x in warehouses if "serverless" in (x.name or "").lower()), warehouses[0])
print("Genie space   :", SPACE_TITLE)
print("Warehouse used:", WAREHOUSE.name)
print("Model endpoint:", fa.CFG["model_endpoint"])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Check the wrapper in the notebook first (no deployment yet)
# MAGIC The same class that the endpoint will run, called directly. Expected: the answer text and, in `custom_outputs`, the tools called.

# COMMAND ----------

from mlflow.types.responses import ResponsesAgentRequest
import fizzco_serving_agent as sa

for q in ["Why did sell_in fail on 31 March and what do I do?", "What is 12 times 12?"]:
    resp = sa.AGENT.predict(ResponsesAgentRequest(input=[{"role": "user", "content": q}]))
    print("QUESTION:", q)
    print("ANSWER  :", resp.output[0].content[0]["text"])
    print("TOOLS   :", resp.custom_outputs)
    print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Log the agent with MLflow
# MAGIC The resources tell Databricks which things the endpoint may use (model endpoint, function, runbook index, Genie space, warehouse); it then gives the endpoint access to exactly those.

# COMMAND ----------

here = os.getcwd()
with mlflow.start_run(run_name="fizzco-agent-6-5"):
    model_info = mlflow.pyfunc.log_model(
        name="agent",
        python_model=os.path.join(here, "fizzco_serving_agent.py"),
        code_paths=[os.path.join(here, "fizzco_agent.py")],
        resources=[DatabricksServingEndpoint(fa.CFG["model_endpoint"]),
                   DatabricksFunction(fa.CFG["function_name"]),
                   DatabricksVectorSearchIndex(fa.CFG["index_name"]),
                   DatabricksGenieSpace(SPACE_ID),
                   DatabricksSQLWarehouse(WAREHOUSE.id)],
        input_example={"input": [{"role": "user", "content": "What was the reconciliation status of sell_in on 31 March 2026?"}]},
        pip_requirements=["mlflow>=3.1.3", "databricks-openai", "databricks-sdk>=0.149.0", "unitycatalog-ai[databricks]", "pandas"],
    )
print("logged:", model_info.model_uri)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Register the model in Unity Catalog

# COMMAND ----------

registered = mlflow.register_model(model_info.model_uri, UC_MODEL)
print("registered", UC_MODEL, "version", registered.version)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Deploy to a Model Serving endpoint
# MAGIC `scale_to_zero=True` so the endpoint costs nothing while idle (the first request after idle time is then slow). Stop here and send the error if this cell fails.

# COMMAND ----------

from databricks import agents

deployment = agents.deploy(UC_MODEL, int(registered.version), scale_to_zero=True,
                           environment_vars={"FIZZCO_GENIE_SPACE_ID": SPACE_ID})
ENDPOINT = deployment.endpoint_name
print("endpoint :", ENDPOINT)
print("status   :", deployment.endpoint_url)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Wait until the endpoint is ready
# MAGIC Re-run this cell until it prints READY (it waits up to 20 minutes each time). Screenshot the endpoint page in **Serving** when it is ready.

# COMMAND ----------

deadline = time.time() + 20 * 60
while time.time() < deadline:
    ep = w.serving_endpoints.get(ENDPOINT)
    state = ep.state
    print(time.strftime("%H:%M:%S"), "ready:", state.ready, "| config_update:", state.config_update)
    ready = getattr(state.ready, "value", str(state.ready))                # "READY" or "NOT_READY"
    updating = getattr(state.config_update, "value", str(state.config_update))
    if ready == "READY" and updating != "IN_PROGRESS":
        print("READY")
        break
    time.sleep(30)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Send live requests
# MAGIC Five real questions, then one deliberately empty request to see how an error shows up. The first request can take minutes if the endpoint was scaled to zero.

# COMMAND ----------

def ask_endpoint(question=None, body=None):
    body = body or {"input": [{"role": "user", "content": question}]}
    started = time.time()
    try:
        out = w.api_client.do("POST", f"/serving-endpoints/{ENDPOINT}/invocations", body=body)
        text = out["output"][0]["content"][0]["text"]
        tools = (out.get("custom_outputs") or {}).get("tools_called")
        return {"ok": True, "seconds": round(time.time() - started, 1), "tools": tools, "answer": text, "error": ""}
    except Exception as exc:
        return {"ok": False, "seconds": round(time.time() - started, 1), "tools": None, "answer": "",
                "error": (type(exc).__name__ + ": " + str(exc))[:300]}

LIVE = [
    ("recon", "What was the reconciliation status of the sell_out feed on 31 March 2026?"),
    ("runbook", "The inventory pipeline failed only at the archive step. Do I need to rerun the whole pipeline?"),
    ("genie", "What were net sell-in sales by region?"),
    ("hero", "Why did sell_in fail on 31 March and what do I do?"),
    ("direct", "Hello! What can you help me with?"),
]
rows = []
for label, q in LIVE:
    r = ask_endpoint(q)
    rows.append({"case": label, **r, "question": q})
rows.append({"case": "empty request", **ask_endpoint(body={"input": []}), "question": "(no message)"})
live = pd.DataFrame(rows)
display(live[["case", "ok", "seconds", "tools", "error", "question"]])
print("requests ok:", int(live["ok"].sum()), "of", len(live))

# COMMAND ----------

for _, r in live.iterrows():
    print("=" * 100)
    print(r["case"], "| ok:", r["ok"], "| seconds:", r["seconds"], "| tools:", r["tools"])
    print(r["answer"] or r["error"])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Monitoring
# MAGIC Three views, all from what the platform records. Take the screenshots in this order:
# MAGIC 1. **Serving > your endpoint > Metrics tab**: request rate, latency and error rate charts (they can lag a few minutes behind the requests).
# MAGIC 2. **The inference table** (next cell): one row per request with status code and duration, the sample of logged interactions. It can take up to about an hour to appear.
# MAGIC 3. **Traces** for the endpoint's requests: Experiments, the experiment of this notebook or of the deployment, Traces tab.

# COMMAND ----------

ep = w.serving_endpoints.get(ENDPOINT)
cfg = ep.ai_gateway.inference_table_config if ep.ai_gateway else None
print("AI Gateway inference table config:", cfg)
if cfg and cfg.enabled:
    PAYLOAD = f"{cfg.catalog_name}.{cfg.schema_name}.{cfg.table_name_prefix}_payload"
    print("payload table:", PAYLOAD)

# COMMAND ----------

try:
    log = spark.table(PAYLOAD)
    print("columns:", log.columns)
    want = [c for c in ["request_time", "status_code", "execution_duration_ms", "databricks_request_id"] if c in log.columns]
    display(log.select(*want).orderBy(want[0], ascending=False).limit(20))
except Exception as exc:
    print("The inference table is not readable yet:", type(exc).__name__, str(exc)[:300])
    print("It can take up to about an hour after the first request. Run this cell again later.")

# COMMAND ----------

try:
    if "execution_duration_ms" in log.columns and "status_code" in log.columns:
        log.createOrReplaceTempView("agent_requests")
        display(spark.sql("""
            SELECT COUNT(*) AS requests,
                   SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) AS errors,
                   ROUND(100.0 * SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) / COUNT(*), 1) AS error_rate_pct,
                   ROUND(percentile(execution_duration_ms, 0.5) / 1000, 1) AS p50_seconds,
                   ROUND(percentile(execution_duration_ms, 0.95) / 1000, 1) AS p95_seconds
            FROM agent_requests"""))
except Exception as exc:
    print("Summary not available:", type(exc).__name__, str(exc)[:300])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Clean up (only after all screenshots are taken)
# MAGIC Free Edition limits the number of active endpoints. Deleting the endpoint keeps the registered model, so the deployment can be repeated. Uncomment to run.

# COMMAND ----------

# w.serving_endpoints.delete(ENDPOINT)
