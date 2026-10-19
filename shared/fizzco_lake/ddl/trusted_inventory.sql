-- Synthetic DDL: trusted_inventory
CREATE TABLE IF NOT EXISTS fizzco_trusted.trusted_inventory (
  snapshot_date DATE, dc_id STRING, sku STRING, stock_on_hand INT
)
USING DELTA
LOCATION 'abfss://fizzco-landing@fizzcostorage.dfs.core.windows.net/trusted/inventory';
