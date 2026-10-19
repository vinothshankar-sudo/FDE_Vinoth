# Subagent's returned file list

Subagent: `fizzco-raw-search` (read-only, called with `runSubagent`). Scope: `shared/fizzco_lake`, docs excluded, `fizzco-raw-archive` excluded. The subagent edited nothing.

The table below is what it returned, with the correct per-file line number added by a human check (the line numbers the subagent returned were wrong for 9 of 11 rows: they were counted across files, not within each file).

| # | File | Returned line | Actual line | Matching text |
|---|---|---|---|---|
| 1 | `adf/pl_fizzco_inventory_load.json` | 12 | 12 | `"sink": {"container": "fizzco-raw", "folder": "raw/inventory/"}` |
| 2 | `adf/pl_fizzco_inventory_load.json` | 20 | 20 | `"baseParameters": {"container": "fizzco-raw", ...}` |
| 3 | `adf/pl_fizzco_promo_load.json` | 43 | 12 | `"sink": {"container": "fizzco-raw", "folder": "raw/promo/"}` |
| 4 | `adf/pl_fizzco_promo_load.json` | 51 | 20 | `"baseParameters": {"container": "fizzco-raw", ...}` |
| 5 | `adf/pl_fizzco_sell_in_load.json` | 68 | 12 | `"sink": {"container": "fizzco-raw", "folder": "raw/sell_in/"}` |
| 6 | `adf/pl_fizzco_sell_in_load.json` | 76 | 20 | `"baseParameters": {"container": "fizzco-raw", ...}` |
| 7 | `ddl/trusted_inventory.sql` | 152 | 6 | `LOCATION 'abfss://fizzco-raw@fizzcostorage.dfs.core.windows.net/trusted/inventory';` |
| 8 | `ddl/trusted_sell_in.sql` | 202 | 6 | `LOCATION 'abfss://fizzco-raw@fizzcostorage.dfs.core.windows.net/trusted/sell_in';` |
| 9 | `ddl/trusted_promo.sql` | 208 | 6 | `LOCATION 'abfss://fizzco-raw@fizzcostorage.dfs.core.windows.net/trusted/promo';` |
| 10 | `databricks/config.py` | 248 | 3 | `CONTAINER = "fizzco-raw"` |
| 11 | `databricks/inventory_transform.py` | 338 | 6 | `SOURCE_URI = "abfss://fizzco-raw@fizzcostorage.dfs.core.windows.net/raw/inventory/"` |

Correct: 11 matches in 8 files, the archive container excluded, the hard-coded URI in `inventory_transform.py` found.
Wrong: line numbers in rows 3 to 11.
