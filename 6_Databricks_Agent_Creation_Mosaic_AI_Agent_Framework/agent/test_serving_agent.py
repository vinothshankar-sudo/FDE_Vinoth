"""Offline checks for the Model Serving wrapper (no Databricks needed): python test_serving_agent.py"""
import os
import sys
import tempfile

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mlflow
from mlflow.types.responses import ResponsesAgentRequest

import fizzco_serving_agent as sa

FAILED = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  " + str(detail)))
    if not ok:
        FAILED.append(name)


calls = []


def fake_run_agent(question, enabled=None, client=None):
    calls.append({"question": question, "enabled": enabled, "genie": sa.fa.CFG["genie_space_id"]})
    return {"answer": "answer to: " + question, "tool_calls": [{"name": "get_recon_status", "arguments": "{}", "ok": True}], "rounds": 2}


sa.fa.run_agent = fake_run_agent


def req(*messages):
    return ResponsesAgentRequest(input=list(messages))


# 1. a plain string message
r = sa.AGENT.predict(req({"role": "user", "content": "Why did sell_in fail?"}))
check("one text output item with the answer", len(r.output) == 1 and r.output[0].content[0]["text"] == "answer to: Why did sell_in fail?", r.output)
check("custom_outputs list the tools called and the rounds", r.custom_outputs == {"tools_called": ["get_recon_status"], "rounds": 2}, r.custom_outputs)

# 2. list-style content
r = sa.AGENT.predict(req({"role": "user", "content": [{"type": "input_text", "text": "part one"}, {"type": "input_text", "text": "part two"}]}))
check("list content parts are joined", calls[-1]["question"] == "part one part two", calls[-1])

# 3. newest user message wins
sa.AGENT.predict(req({"role": "user", "content": "old"}, {"role": "assistant", "content": "ok"}, {"role": "user", "content": "new"}))
check("the newest user message is used", calls[-1]["question"] == "new", calls[-1])

# 4. no user text is refused
try:
    sa.AGENT.predict(req({"role": "assistant", "content": "hi"}))
    check("a request without a user message is refused", False, "no error")
except ValueError:
    check("a request without a user message is refused", True)

# 5. environment settings
os.environ["FIZZCO_TOOLS"] = "get_recon_status, search_runbooks"
os.environ["FIZZCO_GENIE_SPACE_ID"] = "space-123"
sa.AGENT.predict(req({"role": "user", "content": "q"}))
check("FIZZCO_TOOLS limits the tools offered", calls[-1]["enabled"] == ["get_recon_status", "search_runbooks"], calls[-1])
check("FIZZCO_GENIE_SPACE_ID reaches the agent config", calls[-1]["genie"] == "space-123", calls[-1])
del os.environ["FIZZCO_TOOLS"]
sa.AGENT.predict(req({"role": "user", "content": "q"}))
check("without FIZZCO_TOOLS all tools are offered", calls[-1]["enabled"] is None, calls[-1])

# 6. the file can be logged as a model from code with the declared resources
from mlflow.models.resources import (DatabricksFunction, DatabricksGenieSpace, DatabricksServingEndpoint,
                                     DatabricksSQLWarehouse, DatabricksVectorSearchIndex)
with tempfile.TemporaryDirectory() as tmp:
    mlflow.set_tracking_uri("sqlite:///" + os.path.join(tmp, "mlflow.db"))
    mlflow.set_experiment("offline-serving-test")
    with mlflow.start_run():
        info = mlflow.pyfunc.log_model(
            name="agent", python_model=os.path.join(HERE, "fizzco_serving_agent.py"),
            code_paths=[os.path.join(HERE, "fizzco_agent.py")],
            resources=[DatabricksServingEndpoint("databricks-meta-llama-3-3-70b-instruct"),
                       DatabricksFunction("workspace.fizzco.get_recon_status"),
                       DatabricksVectorSearchIndex("workspace.fizzco.runbook_chunks_index"),
                       DatabricksGenieSpace("space-123"), DatabricksSQLWarehouse("wh-123")],
            input_example={"input": [{"role": "user", "content": "hello"}]},
            pip_requirements=["mlflow>=3.1.3", "databricks-openai", "databricks-sdk>=0.149.0", "unitycatalog-ai[databricks]"])
    check("logged as a model from code", bool(info.model_uri), info)
    from mlflow.models import Model
    res = (Model.load(info.model_uri).resources or {}).get("databricks", {})
    kinds = sorted(res.keys()) if isinstance(res, dict) else []
    check("the five resources are recorded in the model", kinds == ["function", "genie_space", "serving_endpoint", "sql_warehouse", "vector_search_index"], res)

print()
print("ALL PASSED" if not FAILED else "FAILED: " + ", ".join(FAILED))
sys.exit(1 if FAILED else 0)
