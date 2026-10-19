"""Fizzco agent wrapped for Model Serving (Module 6, Scenario 6.5). Synthetic data only.

MLflow "models from code": this file is logged with mlflow.pyfunc.log_model(python_model="fizzco_serving_agent.py",
code_paths=["fizzco_agent.py"]). The endpoint receives a Responses-style request, runs the same loop as the notebooks
(fizzco_agent.run_agent) and returns the answer as one text item. No credentials are in this file: on the endpoint the
platform supplies them for the resources declared when the model was logged.

Settings that are not secrets arrive as environment variables set at deploy time:
  FIZZCO_TOOLS            comma-separated tool names to offer (default: all three)
  FIZZCO_GENIE_SPACE_ID   id of the Genie space that ask_genie uses
"""
import os
import uuid

import mlflow
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import ResponsesAgentRequest, ResponsesAgentResponse

import fizzco_agent as fa


def _field(obj, name):
    return obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)


def _text_of(content):
    if isinstance(content, str):
        return content
    parts = []
    for part in content or []:
        text = _field(part, "text")
        if text:
            parts.append(text)
    return " ".join(parts)


def last_user_question(request):
    """The text of the newest user message in the request."""
    for item in reversed(list(request.input)):
        if _field(item, "role") == "user":
            text = _text_of(_field(item, "content")).strip()
            if text:
                return text
    raise ValueError("The request has no user message with text.")


def enabled_tools():
    raw = os.environ.get("FIZZCO_TOOLS", "").strip()
    return [t.strip() for t in raw.split(",") if t.strip()] or None


class FizzcoAgent(ResponsesAgent):
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        question = last_user_question(request)
        space_id = os.environ.get("FIZZCO_GENIE_SPACE_ID", "").strip()
        if space_id:
            fa.CFG["genie_space_id"] = space_id
        result = fa.run_agent(question, enabled=enabled_tools())
        item = self.create_text_output_item(text=result["answer"], id=str(uuid.uuid4()))
        return ResponsesAgentResponse(
            output=[item],
            custom_outputs={"tools_called": [c["name"] for c in result["tool_calls"]], "rounds": result["rounds"]},
        )


AGENT = FizzcoAgent()
mlflow.models.set_model(AGENT)
