-- Synthetic DDL: trusted_promo
CREATE TABLE IF NOT EXISTS fizzco_trusted.trusted_promo (
  promo_id STRING, sku STRING, retailer_id STRING, start_date DATE, end_date DATE, discount_pct INT, promo_days INT
)
USING DELTA
LOCATION 'abfss://fizzco-landing@fizzcostorage.dfs.core.windows.net/trusted/promo';
