"""Offline check of the runbooks tab: normal answer, wrong endpoint name, and a time limit.
No network and no Databricks: the SDK, the SQL connector and the warehouse are replaced by fakes.
Run: pip install streamlit databricks-sdk==0.149.0 databricks-sql-connector pandas pyarrow; python3 test_failure_paths.py
"""
import os, sys, time
from types import SimpleNamespace as NS
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.update({"DATABRICKS_WAREHOUSE_ID": "w", "GENIE_SPACE_ID": "g", "VECTOR_INDEX_NAME": "i", "CHAT_ENDPOINT": "good-endpoint"})
import databricks.sdk as sdk
from databricks.sdk.errors import NotFound, TemporarilyUnavailable

class FakeW:
    class vector_search_indexes:
        @staticmethod
        def query_index(**kw):
            cols = [NS(name=n) for n in ["chunk_id","doc_id","feed","doc_type","section","text"]]
            rows = [[f"C{i}#c1", f"C{i}", "sell_in", "runbook", f"Section {i}", f"text of chunk {i}"] for i in range(1, 6)]
            return NS(manifest=NS(columns=cols), result=NS(data_array=rows))
    class serving_endpoints:
        mode = {"slow": False}
        @staticmethod
        def query(name, **kw):
            if name == "fizzco-no-such-endpoint":
                raise NotFound("Endpoint fizzco-no-such-endpoint does not exist")
            if FakeW.serving_endpoints.mode["slow"]:
                time.sleep(3)
            return NS(choices=[NS(message=NS(content="Cause: off-by-one [S1]. Fix: use <= [S2]."))])
sdk.WorkspaceClient = lambda *a, **k: FakeW()
import databricks.sql as dsql
class FakeConn:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def cursor(self): return self
    def execute(self, q): pass
    def fetchall_arrow(self):
        import pandas as pd
        return NS(to_pandas=lambda: pd.DataFrame({"recon_id": ["R1"]}))
dsql.connect = lambda **k: FakeConn()
import databricks.sdk.core as core
core.Config = lambda: NS(host="h", authenticate=lambda: {})

from streamlit.testing.v1 import AppTest
def run(mode_index, slow=False):
    FakeW.serving_endpoints.mode["slow"] = slow
    at = AppTest.from_file(os.path.join(HERE, "app.py"), default_timeout=30).run()
    at.radio[0].set_value(at.radio[0].options[mode_index]).run()
    at.text_input[1].set_value("Why did it fail?")
    at.button[1].click().run()  # second form button = Ask the runbooks (first is Ask Genie)
    return at
def text(at):
    return " | ".join([m.value for m in at.markdown] + [w.value for w in at.warning] + [e.value for e in at.error] + [c.value for c in at.code])
EXPECT = {"normal": "Cause: off-by-one [S1]", "wrong endpoint": "could not be found", "timeout": "took too long"}
for name, idx, slow in [("normal", 0, False), ("wrong endpoint", 1, False), ("timeout", 2, True)]:
    at = run(idx, slow)
    shown = text(at)
    ok = len(at.exception) == 0 and EXPECT[name] in shown and "Traceback" not in shown
    print(("PASS " if ok else "FAIL ") + name + " | uncaught exceptions: " + str(len(at.exception)))
    if not ok:
        print(shown[:700])
        raise SystemExit(1)
print("all failure paths behave")
