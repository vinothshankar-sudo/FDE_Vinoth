"""Release 2 checks: the chart of differing rows, offline. Release 1 checks are kept in test_release_1.py and still run.
Run: python3 test_release.py"""
import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pandas as pd
import helpers as H
exec(open(os.path.join(HERE, "test_release_1.py")).read().split("check(\"options come")[0].split("import helpers as H")[1])  # ROWS, COLS, df, check
fails = []
def ck(name, ok):
    print(("PASS " if ok else "FAIL ") + name)
    if not ok: fails.append(name)

frame = H.diff_chart_frame(df)
ck("chart table has one column, diff_rows", list(frame.columns) == ["diff_rows"])
ck("chart has 13 bars, ids in order", list(frame.index) == [f"RECON-{i:04d}" for i in range(1, 14)])
ck("chart values equal the table's diff_rows column", dict(frame["diff_rows"]) == dict(zip(df["recon_id"], df["diff_rows"])))
ck("total differing rows is 3 (only RECON-0009)", int(frame["diff_rows"].sum()) == 3 and frame[frame["diff_rows"] > 0].index.tolist() == ["RECON-0009"])
ck("MISMATCH view charts one bar", len(H.diff_chart_frame(H.filter_recon(df, "MISMATCH"))) == 1)
ck("original table not reordered by the chart helper", list(df["recon_id"]) == [f"RECON-{i:04d}" for i in range(1, 14)])

# the page
import databricks.sdk as sdk, databricks.sdk.core as core, databricks.sql as dsql
from types import SimpleNamespace as NS
os.environ.update({"DATABRICKS_WAREHOUSE_ID": "w", "GENIE_SPACE_ID": "g", "VECTOR_INDEX_NAME": "i", "CHAT_ENDPOINT": "c"})
sdk.WorkspaceClient = lambda *a, **k: NS()
core.Config = lambda: NS(host="h", authenticate=lambda: {})
class Conn:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def cursor(self): return self
    def execute(self, q): pass
    def fetchall_arrow(self): return NS(to_pandas=lambda: df.copy())
dsql.connect = lambda **k: Conn()
from streamlit.testing.v1 import AppTest
at = AppTest.from_file(os.path.join(HERE, "app.py"), default_timeout=30).run()
def captions(a): return " | ".join(c.value for c in a.caption)
def charts(a): return a.get("vega_lite_chart")  # st.bar_chart is a Vega-Lite chart in this Streamlit version
ck("All: one chart and 'total in this view: 3'", len(at.exception) == 0 and len(charts(at)) == 1 and "total in this view: 3" in captions(at))
at.radio[0].set_value("MATCH").run()
ck("MATCH: chart present, total 0", len(at.exception) == 0 and len(charts(at)) == 1 and "total in this view: 0" in captions(at))
at.radio[0].set_value("MISMATCH").run()
ck("MISMATCH: chart present, total 3", len(at.exception) == 0 and len(charts(at)) == 1 and "total in this view: 3" in captions(at))
print("all release 2 checks pass" if not fails else "FAILED: " + ", ".join(fails))
sys.exit(1 if fails else 0)
