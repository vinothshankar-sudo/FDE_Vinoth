"""Evaluation helpers for Scenario 6.3: the eval set loader and two code-based scorers (no LLM judge needed).

eval_set.csv columns:
  id, kind, question,
  must_contain    facts the answer must contain, separated by ';'. Inside one fact, '/' separates accepted alternatives.
                  Numbers are compared without thousands separators, text without case.
  expected_facts  the same facts as plain sentences, used only by the optional LLM judge (Correctness)
  expected_tools  tools that must be called, separated by ';' (empty: no requirement)
  forbidden_tools tools that must NOT be called, ';'-separated, or ALL (a direct answer is expected)
"""
import csv

from mlflow.entities import Feedback, SpanType
from mlflow.genai.scorers import scorer

ALL_TOOLS = ["get_recon_status", "search_runbooks", "ask_genie"]


def _split(value, sep=";"):
    return [p.strip() for p in (value or "").split(sep) if p.strip()]


def load_eval_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_dataset(rows, with_judge_facts=False):
    """Rows of eval_set.csv -> the list-of-dicts form mlflow.genai.evaluate accepts."""
    data = []
    for r in rows:
        forbidden = ALL_TOOLS if r["forbidden_tools"].strip().upper() == "ALL" else _split(r["forbidden_tools"])
        expectations = {"must_contain": _split(r["must_contain"]), "expected_tools": _split(r["expected_tools"]),
                        "forbidden_tools": forbidden, "case_id": r["id"], "kind": r["kind"]}
        if with_judge_facts:
            expectations["expected_facts"] = _split(r["expected_facts"])
        data.append({"inputs": {"question": r["question"]}, "expectations": expectations})
    return data


def normalize(text):
    return str(text).lower().replace(",", "").replace("*", "").replace("`", "")


def missing_facts(answer, facts):
    """Facts (each a '/'-separated list of alternatives) that none of whose alternatives appear in the answer."""
    ans = normalize(answer)
    return [f for f in facts if not any(normalize(alt.strip()) in ans for alt in f.split("/") if alt.strip())]


def tools_called(trace):
    """Names of the tools the agent called, read from the trace (tool and retriever spans)."""
    spans = list(trace.search_spans(span_type=SpanType.TOOL)) + list(trace.search_spans(span_type=SpanType.RETRIEVER))
    return sorted({s.name for s in spans})


def tool_verdict(called, expected, forbidden):
    """(ok, reason) for the tools actually called."""
    lacking = [t for t in expected if t not in called]
    wrongly = [t for t in forbidden if t in called]
    if lacking:
        return False, f"missing tool(s): {', '.join(lacking)}; called: {', '.join(called) or 'none'}"
    if wrongly:
        return False, f"tool(s) used that should not be: {', '.join(wrongly)}"
    return True, f"called: {', '.join(called) or 'none'}"


@scorer
def contains_expected_facts(outputs, expectations):
    facts = expectations.get("must_contain", [])
    lacking = missing_facts(outputs, facts)
    return Feedback(value=not lacking, rationale="all facts present" if not lacking else "missing: " + "; ".join(lacking))


@scorer
def uses_the_right_tools(trace, expectations):
    ok, reason = tool_verdict(tools_called(trace), expectations.get("expected_tools", []), expectations.get("forbidden_tools", []))
    return Feedback(value=ok, rationale=reason)
