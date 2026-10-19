"""Offline check of the Access check tab when user authorization is NOT enabled (no forwarded token).
Run: pip install streamlit databricks-sdk==0.149.0 databricks-sql-connector pandas pyarrow; python3 test_access_tab.py"""
import os, sys
from types import SimpleNamespace as NS
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.update({"DATABRICKS_WAREHOUSE_ID": "w", "GENIE_SPACE_ID": "g", "VECTOR_INDEX_NAME": "i", "CHAT_ENDPOINT": "c"})
import pandas as pd
import databricks.sdk as sdk
import databricks.sdk.core as core
import databricks.sql as dsql
sdk.WorkspaceClient = lambda *a, **k: NS()
core.Config = lambda: NS(host="h", authenticate=lambda: {})
class FakeConn:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def cursor(self): return self
    def execute(self, q): self.q = q
    def fetchall_arrow(self):
        return NS(to_pandas=lambda: pd.DataFrame({"signed_in_as": ["app"], "region": ["West"], "rows_visible": [1], "net_sell_in": [1.0], "recon_id": ["R1"], "status": ["MATCH"]}))
dsql.connect = lambda **k: FakeConn()
from streamlit.testing.v1 import AppTest
at = AppTest.from_file(os.path.join(HERE, "app.py"), default_timeout=30).run()
next(b for b in at.button if b.label == "Show my view").click().run()
shown = " | ".join([i.value for i in at.info] + [w.value for w in at.warning] + [e.value for e in at.error])
ok = len(at.exception) == 0 and "User authorization is not enabled" in shown
print(("PASS" if ok else "FAIL") + " no token: friendly info, no exception")
if not ok:
    print(shown); raise SystemExit(1)

# Second check: the user's own query fails (e.g. scope not effective) while the app's query works.
# Expect: the user part shows the error chain, the app part still shows its rows, no exception.
import streamlit as st
class Boom(Exception): pass
def connect(**k):
    if "access_token" in k:
        try:
            raise Boom("403 invalid scope")
        except Boom as inner:
            raise dsql.RequestError("Error during request to server", {"http-code": 403, "error-message": "scope missing"}) from inner
    return FakeConn()
dsql.connect = connect
st.context = NS(headers={"x-forwarded-access-token": "not-a-real-token"})
at = AppTest.from_file(os.path.join(HERE, "app.py"), default_timeout=30).run()
next(b for b in at.button if b.label == "Show my view").click().run()
errs = " | ".join(e.value for e in at.error)
texts = " | ".join(t.value for t in at.text)
ok2 = (len(at.exception) == 0 and "your own permissions" in errs and "Error during request to server" in texts
       and "403 invalid scope" in texts and "scope missing" in texts and len(at.dataframe) == 2)  # recon table + the app view
print(("PASS" if ok2 else "FAIL") + " user view fails, app view still shown, error chain visible")
if not ok2:
    print(errs, texts, len(at.dataframe)); raise SystemExit(1)
