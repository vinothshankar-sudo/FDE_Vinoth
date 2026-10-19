---
doc_id: DD-GOLD-001
title: Data dictionary - gold tables
doc_type: dictionary
feed: all
owner: Fizzco Data Engineering (fictional team)
last_reviewed: 2026-04-02
---
# Data dictionary: gold tables

All tables are in the catalog `workspace`, schema `fizzco`. All data is synthetic and covers the first quarter of 2026.

## gold_sell_in_vs_sell_out
Grain: one row per week, retailer and SKU. Compares what Fizzco shipped to retailers (sell-in) with what retailers sold to shoppers (sell-out). Columns: `week_start` (the Monday that starts the sales week), `region` (East or West), `retailer_id`, `sku`, `sell_in_units`, `sell_in_gross_amount`, `sell_in_discount_amount`, `sell_in_net_amount` (gross minus discount), `sell_out_units`, `sell_out_amount` (value at shelf price), `variance_units` (sell-in units minus sell-out units) and `variance_pct`. The table has 68 rows.

## gold_recon_results
Grain: one row per reconciliation run. Columns: `recon_id` (format RECON-####), `job_id` (format JOB-####), `feed` (sell_in, sell_out, inventory or promo), `recon_date` (inclusive cut-off date), `source_rows`, `trusted_rows`, `diff_rows` (source minus trusted), `status` (MATCH or MISMATCH) and `note`. The table has 13 rows and includes the 31 March 2026 sell_in mismatch and its rerun.

## gold_promo_performance
Grain: one row per promotion. Columns: `promo_id` (format PROMO-2026-####), `sku`, `retailer_id`, `region`, `start_date`, `end_date`, `discount_pct` (5, 10, 15 or 20), `promo_days`, `baseline_units`, `promo_units`, `incremental_units`, `uplift_pct` and `promo_cost`. The table has 12 rows.

## dim_retailer
One row per retailer. Columns: `retailer_id` (R001 to R010), `retailer_name`, `region` (East or West) and `channel` (Supermarket, Convenience or Discount). The table has 10 rows.

## dim_product
One row per product. Columns: `sku` (for example FZ-COLA-330), `product_name`, `category` (Beverage or Snack), `pack_size` and `list_price`. The table has 8 rows.

## Trusted tables
The trusted layer holds cleaned copies of the raw feeds: `trusted_sell_in` (adds `net_amount`), `trusted_sell_out` (sale_date, retailer_id, sku, units, sale_amount), `trusted_inventory` (snapshot_date, dc_id, sku, stock_on_hand) and `trusted_promo` (adds `promo_days`).
