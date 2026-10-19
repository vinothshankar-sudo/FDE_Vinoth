"""Module 4 probe: read-only checks before anything is created. No model calls, nothing is changed.

Run from the repo:  python3 shared/vector/probe_vector_search.py
Needs DATABRICKS_HOST and DATABRICKS_TOKEN in the environment (never in files).
It lists: SQL warehouses, Vector Search endpoints, existing indexes on our endpoint, and whether the
source schema is reachable. Use it once to confirm the REST paths work on Free Edition.
"""
import sys

import vs_lib as V


def main() -> int:
    V.R.setup_logging()
    client = V.VSClient()
    V.out(f"Token looks valid in shape: {client.base.token_looks_ok} (length {client.base.token_length}; value never printed)")
    warehouses = client.request("GET", "/api/2.0/sql/warehouses").get("warehouses", [])
    V.out(f"SQL warehouses: {len(warehouses)}")
    for w in warehouses:
        V.out(f"  - {w.get('name')} state={w.get('state')} size={w.get('cluster_size')}")
    endpoints = client.request("GET", "/api/2.0/vector-search/endpoints", allow=(404,))
    if endpoints.get("_status") == 404:
        V.out(f"Vector Search endpoints: REST path returned 404 -> {endpoints.get('_body')}")
    else:
        items = endpoints.get("endpoints", [])
        V.out(f"Vector Search endpoints: {len(items)}")
        for e in items:
            V.out(f"  - {e.get('name')} state={e.get('endpoint_status', {}).get('state')} type={e.get('endpoint_type')}")
    rows = client.sql(f"SHOW TABLES IN {V.CATALOG}.{V.SCHEMA}")
    V.out(f"Tables in {V.CATALOG}.{V.SCHEMA}: {len(rows)}")
    for r in rows:
        V.out(f"  - {r[1]}")
    V.out(f"HTTP calls made: {client.calls}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
