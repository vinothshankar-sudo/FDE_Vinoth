-- Synthetic DDL: trusted_sell_in
CREATE TABLE IF NOT EXISTS fizzco_trusted.trusted_sell_in (
  order_date DATE, retailer_id STRING, sku STRING, units INT, gross_amount DECIMAL(12,2), discount_amount DECIMAL(12,2), net_amount DECIMAL(12,2)
)
USING DELTA
LOCATION 'abfss://fizzco-landing@fizzcostorage.dfs.core.windows.net/trusted/sell_in';
