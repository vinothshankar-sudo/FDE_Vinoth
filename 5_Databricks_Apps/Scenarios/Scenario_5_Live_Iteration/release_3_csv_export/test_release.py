"""Release 3 checks: the CSV export of the rows shown, offline. Releases 1 and 2 checks are kept in test_release_1.py and test_release_2.py.
Run: python3 test_release.py"""
import os, sys, io
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pandas as pd
import helpers as H
exec(open(os.path.join(HERE, "test_release_1.py")).read().split("check(\"options come")[0].split("import helpers as H")[1])  # ROWS, COLS, df, check
fails = []
def ck(name, ok):
    print(("PASS " if ok else "FAIL ") + name)
    if not ok: fails.append(name)

def back(data):  # read the exported bytes the way a spreadsheet tool would
    return pd.read_csv(io.BytesIO(data), dtype=str)

for choice, n in [("All", 13), ("MATCH", 12), ("MISMATCH", 1)]:
    shown = H.filter_recon(df, choice)
    out = back(H.to_csv_bytes(shown))
    ck(f"{choice}: file has {n} data rows and the 8 columns, no row-number column",
       len(out) == n and list(out.columns) == COLS)
    ck(f"{choice}: every value equals what the table shows",
       out.equals(shown.astype(str).reset_index(drop=True)))
raw = H.to_csv_bytes(H.filter_recon(df, "MISMATCH")).decode("utf-8").strip().splitlines()
ck("MISMATCH file text: header + RECON-0009 line", len(raw) == 2 and raw[1] == "RECON-0009,JOB-0049,sell_in,2026-03-31,63,60,3,MISMATCH")
ck("file names say what is inside", [H.export_filename(s) for s in ("All", "MATCH", "MISMATCH")] == ["recon_status_all.csv", "recon_status_match.csv", "recon_status_mismatch.csv"])
ck("odd status text gives a safe file name", H.export_filename("A/B ../x") == "recon_status_a_b_x.csv")
ck("empty selection exports a header-only file", back(H.to_csv_bytes(H.filter_recon(df, "OTHER"))).shape == (0, 8))

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
btn = at.get("download_button")
ck("page shows one download button labelled (13 rows)", len(at.exception) == 0 and len(btn) == 1 and "(13 rows)" in str(btn[0].proto.label))
at.radio[0].set_value("MISMATCH").run()
btn = at.get("download_button")
ck("after MISMATCH the button says (1 row)", len(btn) == 1 and "(1 row)" in str(btn[0].proto.label))
print("all release 3 checks pass" if not fails else "FAILED: " + ", ".join(fails))
sys.exit(1 if fails else 0)
