"""Read-only: print how the Module 4 index is configured (type, source table, embedding model, sync mode).

Run:  python3 shared/vector/show_index_spec.py
One REST status call; no model calls; creates and changes nothing. Used as evidence for Scenario 4.1.
"""
import json
import sys

import vs_lib as V


def main() -> int:
    client = V.VSClient()
    info = client.index_get()
    if info is None:
        V.out(f"Index {V.INDEX} does not exist")
        return 1
    spec = info.get("delta_sync_index_spec", {})
    V.out(f"Index:               {info.get('name')}")
    V.out(f"Endpoint:            {info.get('endpoint_name')}")
    V.out(f"Index type:          {info.get('index_type')}")
    V.out(f"Primary key:         {info.get('primary_key')}")
    V.out(f"Source table:        {spec.get('source_table')}")
    V.out(f"Pipeline (sync):     {spec.get('pipeline_type')}")
    V.out("Embedding source:    " + json.dumps(spec.get("embedding_source_columns")))
    V.out(f"Indexed rows:        {info.get('status', {}).get('indexed_row_count')}   ready={info.get('status', {}).get('ready')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
