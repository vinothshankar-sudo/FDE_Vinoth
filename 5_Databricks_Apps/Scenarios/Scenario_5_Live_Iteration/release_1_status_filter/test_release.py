"""Release 1 checks: the status filter, offline. The 13 rows are the synthetic recon results from the Fizzco lake (gold_recon_results).
Run: python3 test_release.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pandas as pd
import helpers as H

ROWS = [
    ("RECON-0001", "JOB-0041", "sell_in", "2026-01-31", 24, 24, 0, "MATCH"),
    ("RECON-0002", "JOB-0042", "sell_out", "2026-01-31", 48, 48, 0, "MATCH"),
    ("RECON-0003", "JOB-0043", "inventory", "2026-01-31", 10, 10, 0, "MATCH"),
    ("RECON-0004", "JOB-0044", "promo", "2026-01-31", 8, 8, 0, "MATCH"),
    ("RECON-0005", "JOB-0045", "sell_in", "2026-02-28", 38, 38, 0, "MATCH"),
    ("RECON-0006", "JOB-0046", "sell_out", "2026-02-28", 78, 78, 0, "MATCH"),
    ("RECON-0007", "JOB-0047", "inventory", "2026-02-28", 29, 29, 0, "MATCH"),
    ("RECON-0008", "JOB-0048", "promo", "2026-02-28", 12, 12, 0, "MATCH"),
    ("RECON-0009", "JOB-0049", "sell_in", "2026-03-31", 63, 60, 3, "MISMATCH"),
    ("RECON-0010", "JOB-0050", "sell_out", "2026-03-31", 127, 127, 0, "MATCH"),
    ("RECON-0011", "JOB-0051", "inventory", "2026-03-31", 40, 40, 0, "MATCH"),
    ("RECON-0012", "JOB-0052", "promo", "2026-03-31", 12, 12, 0, "MATCH"),
    ("RECON-0013", "JOB-0053", "sell_in", "2026-03-31", 63, 63, 0, "MATCH"),
]
COLS = ["recon_id", "job_id", "feed", "recon_date", "source_rows", "trusted_rows", "diff_rows", "status"]
df = pd.DataFrame(ROWS, columns=COLS)
fails = []
def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name)
    if not ok: fails.append(name)

check("options come from the data: All, MATCH, MISMATCH", H.status_options(df) == ["All", "MATCH", "MISMATCH"])
check("All returns all 13 rows", len(H.filter_recon(df, "All")) == 13)
check("MATCH returns 12 rows", len(H.filter_recon(df, "MATCH")) == 12)
mm = H.filter_recon(df, "MISMATCH")
check("MISMATCH returns exactly RECON-0009 (sell_in, 31 March, 3 rows differ)",
      list(mm["recon_id"]) == ["RECON-0009"] and int(mm["diff_rows"].iloc[0]) == 3)
check("a status that is not present returns no rows, no error", len(H.filter_recon(df, "OTHER")) == 0)
check("the filter does not change the original table", len(df) == 13)
check("missing status values are ignored in the options", H.status_options(pd.DataFrame({"status": ["MATCH", None]})) == ["All", "MATCH"])

# the page itself, with the query faked
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
check("page starts with 13 of 13 rows and no exception", len(at.exception) == 0 and any("Showing 13 of 13 rows" in c.value for c in at.caption))
at.radio[0].set_value("MISMATCH").run()
check("choosing MISMATCH shows 1 of 13 rows", len(at.exception) == 0 and any("Showing 1 of 13 rows" in c.value for c in at.caption))
at.radio[0].set_value("MATCH").run()
check("choosing MATCH shows 12 of 13 rows", any("Showing 12 of 13 rows" in c.value for c in at.caption))
print("all release 1 checks pass" if not fails else "FAILED: " + ", ".join(fails))
sys.exit(1 if fails else 0)
