"""Read-only status check for the Module 4 endpoint and index. Safe to run while a build script is running.

Run:  python3 shared/vector/status_vector_search.py          (one check)
      python3 shared/vector/status_vector_search.py watch    (repeat every 30 s until Ctrl+C)
Makes 2 REST status calls per check and no model or SQL calls. Creates and changes nothing.
"""
import sys
import time

import vs_lib as V


def check(client) -> None:
    state = client.endpoint_state()
    V.out(f"[{V.stamp()}] endpoint {V.ENDPOINT}: {state if state else 'does not exist yet'}")
    info = client.index_get()
    if info is None:
        V.out(f"[{V.stamp()}] index {V.INDEX}: does not exist yet")
        return
    status = info.get("status", {})
    V.out(f"[{V.stamp()}] index: ready={status.get('ready')} indexed_rows={status.get('indexed_row_count')} message={status.get('message')}")


if __name__ == "__main__":
    client = V.VSClient()
    if len(sys.argv) > 1 and sys.argv[1] == "watch":
        while True:
            check(client)
            time.sleep(30)
    else:
        check(client)
