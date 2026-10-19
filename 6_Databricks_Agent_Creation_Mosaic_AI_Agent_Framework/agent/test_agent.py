"""Offline checks of the agent loop with a scripted fake model and fake tools. Run: python3 test_agent.py"""
import json, os, sys, tempfile
from types import SimpleNamespace as NS
os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mlflow
mlflow.set_tracking_uri("sqlite:///" + os.path.join(tempfile.mkdtemp(), "mlflow.db"))  # local test store only
mlflow.set_experiment("offline-agent-test")
import fizzco_agent as fa

fails = []
def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name)
    if not ok: fails.append(name)

def call(i, name, args):
    return NS(id=f"c{i}", function=NS(name=name, arguments=args if isinstance(args, str) else json.dumps(args)))

class FakeClient:
    """Plays a list of replies: ('text', str) or ('tools', [calls]). Records every request."""
    def __init__(self, script):
        self.script, self.requests = list(script), []
        self.chat = NS(completions=NS(create=self.create))
    def create(self, **kw):
        self.requests.append(kw)
        kind, payload = self.script.pop(0)
        msg = NS(content=payload if kind == "text" else None, tool_calls=payload if kind == "tools" else None)
        return NS(choices=[NS(message=msg)])

RECON = ("RECON-0009 | job JOB-0049 | feed sell_in | date 2026-03-31 | source_rows 63 | trusted_rows 60 | diff_rows 3 | status MISMATCH | note x\n"
         "RECON-0013 | job JOB-0053 | feed sell_in | date 2026-03-31 | source_rows 63 | trusted_rows 63 | diff_rows 0 | status MATCH | note rerun")
seen = []
def fake_recon(feed, recon_date):
    seen.append((feed, recon_date)); return RECON
fa.TOOL_FUNCTIONS["get_recon_status"] = fake_recon
fa.TOOL_FUNCTIONS["search_runbooks"] = lambda query: "[RB-SELL-IN-001#c2] (RB-SELL-IN-001; section: x)\nmake the end date inclusive"
def boom(question): raise RuntimeError("space not found")
fa.TOOL_FUNCTIONS["ask_genie"] = boom

# 1 direct answer, no tool
c = FakeClient([("text", "Hello, I can look up reconciliation runs.")])
r = fa.run_agent("Hello!", client=c)
check("direct question: no tool called, one model call", r["tool_calls"] == [] and r["rounds"] == 1 and "Hello" in r["answer"])
check("the request offers three tools with tool_choice auto", len(c.requests[0]["tools"]) == 3 and c.requests[0]["tool_choice"] == "auto")
check("system prompt is first and the question is last", c.requests[0]["messages"][0]["role"] == "system" and c.requests[0]["messages"][-1]["content"] == "Hello!")

# 2 tool path
c = FakeClient([("tools", [call(1, "get_recon_status", {"feed": "sell_in", "recon_date": "2026-03-31"})]), ("text", "Two runs: RECON-0009 MISMATCH, rerun RECON-0013 MATCH.")])
r = fa.run_agent("What happened to sell_in on 31 March?", client=c)
check("tool path: tool called once with the right arguments", fa.tool_names(r) == ["get_recon_status"] and seen[-1] == ("sell_in", "2026-03-31"))
check("tool path: result went back to the model as a tool message", c.requests[1]["messages"][-1] == {"role": "tool", "tool_call_id": "c1", "content": RECON})
check("tool path: assistant tool-call message was kept in the history", c.requests[1]["messages"][-2]["tool_calls"][0]["function"]["name"] == "get_recon_status")
check("tool path: two rounds and the final answer", r["rounds"] == 2 and "RECON-0013" in r["answer"])

# 3 tool restriction
c = FakeClient([("text", "ok")])
fa.run_agent("x", enabled=["get_recon_status"], client=c)
sp = c.requests[0]["messages"][0]["content"]
check("the system prompt names only the tools offered", "get_recon_status(" in sp and "ask_genie(" not in sp and "search_runbooks(" not in sp)
check("the full prompt names all three tools", all(n + "(" in fa.SYSTEM_PROMPT for n in fa.TOOL_SPECS))
c = FakeClient([("text", "ok")])
fa.run_agent("x", enabled=["get_recon_status"], client=c)
check("enabled list limits the tools offered", [t["function"]["name"] for t in c.requests[0]["tools"]] == ["get_recon_status"])
c = FakeClient([("text", "no tools")])
fa.run_agent("x", enabled=[], client=c)
check("no tools: the request has no tools field", "tools" not in c.requests[0])

# 4 failures
c = FakeClient([("tools", [call(1, "ask_genie", {"question": "q"})]), ("text", "Genie failed, so I cannot give the numbers.")])
r = fa.run_agent("sales?", client=c)
check("tool error is reported to the model as text", c.requests[1]["messages"][-1]["content"].startswith("TOOL_ERROR: RuntimeError: space not found") and r["tool_calls"][0]["ok"] is False)
c = FakeClient([("tools", [call(1, "drop_table", {})]), ("text", "done")])
r = fa.run_agent("x", client=c)
check("a tool that does not exist is refused", "not available" in c.requests[1]["messages"][-1]["content"] and r["tool_calls"][0]["ok"] is False)
c = FakeClient([("tools", [call(1, "get_recon_status", "{not json")]), ("text", "done")])
r = fa.run_agent("x", client=c)
check("bad JSON arguments become a tool error, no crash", c.requests[1]["messages"][-1]["content"].startswith("TOOL_ERROR") and r["answer"] == "done")
fa.CFG["max_rounds"] = 3
c = FakeClient([("tools", [call(i, "search_runbooks", {"query": "q"})]) for i in range(1, 4)])
r = fa.run_agent("loop", client=c)
check("a model that never stops is cut off after max_rounds", r["rounds"] == 3 and "too many tool steps" in r["answer"] and len(r["tool_calls"]) == 3)
fa.CFG["max_rounds"] = 6

# 5 helpers
text, ok = fa.run_tool("search_runbooks", json.dumps({"query": "x"}))
check("run_tool returns text and ok", ok and "inclusive" in text)
fa.TOOL_FUNCTIONS["search_runbooks"] = lambda query: "x" * 10000
text, ok = fa.run_tool("search_runbooks", json.dumps({"query": "x"}))
check("very long tool text is truncated", len(text) < 6100 and text.endswith("[truncated]"))
check("format_passages with no rows", fa.format_passages([]) == "No passages found.")
check("format_passages shows chunk id and text", "[C1#c1] (C1; section: S)\nhello" in fa.format_passages([{"chunk_id": "C1#c1", "doc_id": "C1", "section": "S", "text": "hello"}]))
check("tool specs have name, description and required fields", all(s["function"]["description"] and s["function"]["parameters"]["required"] for s in fa.TOOL_SPECS.values()))

# 6 tracing: the agent run produces a trace with agent and tool spans
from mlflow.entities import SpanType
fa.TOOL_FUNCTIONS["get_recon_status"] = mlflow.trace(name="get_recon_status", span_type=SpanType.TOOL)(fake_recon)  # as in the real module
c = FakeClient([("tools", [call(1, "get_recon_status", {"feed": "sell_in", "recon_date": "2026-03-31"})]), ("text", "done")])
fa.run_agent("trace me", client=c)
tid = mlflow.get_last_active_trace_id()
mlflow.flush_trace_async_logging()
trace = mlflow.get_trace(tid)
names = [s.name for s in trace.data.spans]
check("trace has the agent span and the tool span", "fizzco_agent" in names and "get_recon_status" in names)
tool_spans = trace.search_spans(span_type=SpanType.TOOL)
check("the tool span records its inputs and output", tool_spans[0].inputs == {"feed": "sell_in", "recon_date": "2026-03-31"} and "RECON-0009" in str(tool_spans[0].outputs))
print("spans:", names)
rows = fa.trace_summary(trace)
check("trace_summary lists the spans in order with previews", [r["span"] for r in rows][0] == "fizzco_agent" and "RECON-0009" in rows[1]["output"] and rows[1]["type"].endswith("TOOL"))
sql = fa.recon_function_sql()
check("function SQL reads the real table by default", "FROM workspace.fizzco.gold_recon_results r" in sql and sql.startswith("CREATE OR REPLACE FUNCTION workspace.fizzco.get_recon_status("))
check("function SQL can point at another table (used to break the tool in 6.4)", "FROM workspace.fizzco.gold_recon_results_stale r" in fa.recon_function_sql("workspace.fizzco.gold_recon_results_stale"))
file_sql = open(os.path.join(HERE, "..", "Scenarios", "Scenario_1_First_Tool_Calling_Agent", "01_create_get_recon_status.sql")).read()
check("the .sql file starts with the same statement", file_sql.startswith("-- Scenario 6.1") and sql + ";" in file_sql)
fa._CACHE["w"] = NS(genie=NS(list_spaces=lambda: NS(spaces=[NS(title="Retail Sales & Promotions Analytics", space_id="s1"), NS(title="Other", space_id="s2")])))
check("find_genie_space returns the one match", fa.find_genie_space("Retail Sales") == ("s1", "Retail Sales & Promotions Analytics"))
fa._CACHE["w"] = NS(genie=NS(list_spaces=lambda: NS(spaces=[])))
try:
    fa.find_genie_space("Retail Sales"); check("find_genie_space raises when none match", False)
except RuntimeError:
    check("find_genie_space raises when none match", True)
print("all agent checks pass" if not fails else "FAILED: " + ", ".join(fails))
sys.exit(1 if fails else 0)
