"""Offline checks of the eval set, the scorers and a full mlflow.genai.evaluate run with a scripted fake model. Run: python3 test_eval.py"""
import json, os, sys, tempfile
from types import SimpleNamespace as NS
os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mlflow
mlflow.set_tracking_uri("sqlite:///" + os.path.join(tempfile.mkdtemp(), "mlflow.db"))
mlflow.set_experiment("offline-eval-test")
import fizzco_agent as fa, fizzco_eval as fe

fails = []
def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name)
    if not ok: fails.append(name)

rows = fe.load_eval_rows(os.path.join(HERE, "..", "Scenarios", "Scenario_3_Evaluation_Before_Trust", "eval_set.csv"))
check("12 questions, ids unique", len(rows) == 12 and len({r["id"] for r in rows}) == 12)
check("easy, edge, both and direct cases are all present", {r["kind"] for r in rows} == {"easy", "edge", "both", "direct"})
check("every row has facts to check", all(fe._split(r["must_contain"]) and r["expected_facts"] for r in rows))
ds = fe.to_dataset(rows, with_judge_facts=True)
check("dataset has inputs and expectations", ds[0]["inputs"] == {"question": rows[0]["question"]} and ds[0]["expectations"]["expected_tools"] == ["get_recon_status"])
check("ALL forbids the three tools", ds[-1]["expectations"]["forbidden_tools"] == fe.ALL_TOOLS)

check("facts: numbers compared without thousands separator", fe.missing_facts("West 12,463.04 and East 9,893.50", ["12463.04", "9893.5"]) == [])
check("facts: any alternative is enough", fe.missing_facts("Use <= for the end date", ["end date/end-date", "inclusive/<="]) == [])
check("facts: a missing fact is reported", fe.missing_facts("MATCH", ["MATCH", "127"]) == ["127"])
check("tools: missing tool fails", fe.tool_verdict([], ["get_recon_status"], [])[0] is False)
check("tools: forbidden tool fails", fe.tool_verdict(["ask_genie"], [], fe.ALL_TOOLS)[0] is False)
check("tools: extra tool allowed when not forbidden", fe.tool_verdict(["get_recon_status", "ask_genie"], ["get_recon_status"], [])[0] is True)

# A scripted model: right on most questions, deliberately wrong on three (one tool never called, one fact missing, one direct question using a tool).
RECON = "RECON-0009 | job JOB-0049 | MISMATCH | diff 3\nRECON-0013 | job JOB-0053 | MATCH | rerun"
def fake_recon(feed, recon_date):
    return RECON if feed == "sell_in" else "RECON-0010 | job JOB-0050 | MATCH | source_rows 127 | trusted_rows 127"
def fake_rb(query): return "[RB-SELL-IN-001#c2] make the end date inclusive (<=) and rerun"
def fake_genie(question): return "West 12463.04 East 9893.50"
fa.TOOL_FUNCTIONS["get_recon_status"] = mlflow.trace(name="get_recon_status", span_type=fe.SpanType.TOOL)(fake_recon)
fa.TOOL_FUNCTIONS["search_runbooks"] = mlflow.trace(name="search_runbooks", span_type=fe.SpanType.RETRIEVER)(fake_rb)
fa.TOOL_FUNCTIONS["ask_genie"] = mlflow.trace(name="ask_genie", span_type=fe.SpanType.TOOL)(fake_genie)

class Model:
    def __init__(self): self.chat = NS(completions=NS(create=self.create))
    def create(self, **kw):
        msgs = kw["messages"]
        q = msgs[1]["content"]
        if msgs[-1]["role"] == "tool":
            used = " || ".join(m["content"] for m in msgs if m["role"] == "tool")
            return self._text(f"Based on the tools: {used}")
        if q.startswith("What is 12 times"):
            return self._tools("get_recon_status", {"feed": "sell_in", "recon_date": "2026-03-31"})   # wrong: tool for a direct question
        if q.startswith("Hello"):
            return self._text("I can help with reconciliation, runbooks and sales numbers.")
        if "promo on 30 April" in q:
            return self._text("It was a MATCH.")                                                       # wrong: invents a result, no tool
        if "net sell-in sales by region" in q:
            return self._tools("ask_genie", {"question": q})
        if "reconciliation status of the sell_out" in q:
            return self._tools("get_recon_status", {"feed": "sell_out", "recon_date": "2026-03-31"})
        if "sell_in fail" in q or "how many reconciliation runs" in q.lower():
            return self._tools("get_recon_status", {"feed": "sell_in", "recon_date": "2026-03-31"}, also=("search_runbooks", {"query": "end date"}))
        return self._tools("search_runbooks", {"query": q})
    def _text(self, t): return NS(choices=[NS(message=NS(content=t, tool_calls=None))])
    def _tools(self, name, args, also=None):
        calls = [NS(id="a", function=NS(name=name, arguments=json.dumps(args)))]
        if also: calls.append(NS(id="b", function=NS(name=also[0], arguments=json.dumps(also[1]))))
        return NS(choices=[NS(message=NS(content=None, tool_calls=calls))])
fa._CACHE["llm"] = Model()

results = mlflow.genai.evaluate(data=ds, predict_fn=lambda question: fa.ask(question),
                                scorers=[fe.contains_expected_facts, fe.uses_the_right_tools])
table = results.tables["eval_results"]
print(list(table.columns))
check("one row per question", len(table) == 12)
fact_col = next(c for c in table.columns if c.startswith("contains_expected_facts") and c.endswith("value"))
tool_col = next(c for c in table.columns if c.startswith("uses_the_right_tools") and c.endswith("value"))
def verdict(col):
    out = {}
    for _, r in table.iterrows():
        out[r["case_id/value"]] = r[col]
    return out
facts, tools = verdict(fact_col), verdict(tool_col)
print("facts:", facts); print("tools:", tools)
check("scripted failures are caught: X2 no tool, no 'no run' statement", facts["X2"] in (False, "no") and tools["X2"] in (False, "no"))
check("scripted failure: D2 used a tool for a direct question", tools["D2"] in (False, "no"))
check("scripted successes pass both scorers (E1, E6, M1, D1)", all(facts[k] in (True, "yes") and tools[k] in (True, "yes") for k in ["E1", "E6", "M1", "D1"]))
print("all eval checks pass" if not fails else "FAILED: " + ", ".join(fails))
sys.exit(1 if fails else 0)
