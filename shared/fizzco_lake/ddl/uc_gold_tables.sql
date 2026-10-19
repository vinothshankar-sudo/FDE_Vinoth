-- Fizzco Migration Assurance Hub: Unity Catalog gold tables (synthetic data only)
-- Run in the Databricks SQL Editor on a serverless SQL warehouse, one statement block at a time.
--
-- BEFORE YOU RUN (UI steps, do these once):
--   1. Catalog > your catalog > Create schema named: fizzco
--   2. Catalog > fizzco > Create > Volume named: fizzco_landing (managed volume)
--   3. Upload the folder "gold" (it holds 5 files) into the volume, so the files sit in
--      /Volumes/workspace/fizzco/fizzco_landing/gold/ :
--        dim_retailer.csv, dim_product.csv, gold_sell_in_vs_sell_out.csv,
--        gold_recon_results.csv, gold_promo_performance.csv
--      (the repo folder is shared/fizzco_lake/data/gold/)
--   4. If your catalog is not called "workspace", replace "workspace" below (search and replace).

USE CATALOG workspace;
USE SCHEMA fizzco;

-- 1. dim_retailer -----------------------------------------------------------------------
CREATE OR REPLACE TABLE dim_retailer (
  retailer_id   STRING COMMENT 'Retailer code, format R### (R001 to R010). Joins to retailer_id in the gold tables.',
  retailer_name STRING COMMENT 'Fictional retailer chain name.',
  region        STRING COMMENT 'Sales region that owns the retailer: East or West.',
  channel       STRING COMMENT 'Retail channel: Supermarket, Convenience or Discount.'
) COMMENT 'One row per Fizzco retailer with its sales region and channel. Synthetic data.';

INSERT INTO dim_retailer
SELECT retailer_id, retailer_name, region, channel
FROM read_files('/Volumes/workspace/fizzco/fizzco_landing/gold/dim_retailer.csv', format => 'csv', header => true);

-- 2. dim_product ------------------------------------------------------------------------
CREATE OR REPLACE TABLE dim_product (
  sku          STRING COMMENT 'Stock keeping unit code, for example FZ-COLA-330. Joins to sku in the gold tables.',
  product_name STRING COMMENT 'Fictional product name.',
  category     STRING COMMENT 'Product category: Beverage or Snack.',
  pack_size    STRING COMMENT 'Pack size with unit, for example 330 ml or 150 g.',
  list_price   DOUBLE COMMENT 'Fizzco list price per unit in currency units.'
) COMMENT 'One row per Fizzco product (SKU). Synthetic data.';

INSERT INTO dim_product
SELECT sku, product_name, category, pack_size, CAST(list_price AS DOUBLE)
FROM read_files('/Volumes/workspace/fizzco/fizzco_landing/gold/dim_product.csv', format => 'csv', header => true);

-- 3. gold_sell_in_vs_sell_out -------------------------------------------------------------
CREATE OR REPLACE TABLE gold_sell_in_vs_sell_out (
  week_start            DATE   COMMENT 'Monday that starts the sales week (Monday to Sunday).',
  region                STRING COMMENT 'Sales region of the retailer: East or West.',
  retailer_id           STRING COMMENT 'Retailer code. Joins to dim_retailer.retailer_id.',
  sku                   STRING COMMENT 'Product code. Joins to dim_product.sku.',
  sell_in_units         INT    COMMENT 'Units Fizzco invoiced to the retailer that week (orders). 0 if no order that week.',
  sell_in_gross_amount  DOUBLE COMMENT 'Invoiced value of sell-in before discounts.',
  sell_in_discount_amount DOUBLE COMMENT 'Discount given on the sell-in orders.',
  sell_in_net_amount    DOUBLE COMMENT 'Sell-in value after discounts: gross amount minus discount amount.',
  sell_out_units        INT    COMMENT 'Units the retailer sold to shoppers that week (scan data). 0 if none.',
  sell_out_amount       DOUBLE COMMENT 'Value of those shopper sales at shelf price.',
  variance_units        INT    COMMENT 'Sell-in units minus sell-out units for the week. Positive means more shipped than sold.',
  variance_pct          DOUBLE COMMENT 'variance_units as a percentage of sell_in_units. Empty when there was no sell-in that week.'
) COMMENT 'Gold table at week x retailer x SKU grain comparing what Fizzco shipped to retailers (sell-in) with what retailers sold to shoppers (sell-out). Synthetic data, Q1 2026.';

INSERT INTO gold_sell_in_vs_sell_out
SELECT CAST(week_start AS DATE), region, retailer_id, sku, CAST(sell_in_units AS INT),
       CAST(sell_in_gross_amount AS DOUBLE), CAST(sell_in_discount_amount AS DOUBLE),
       CAST(sell_in_net_amount AS DOUBLE), CAST(sell_out_units AS INT),
       CAST(sell_out_amount AS DOUBLE), CAST(variance_units AS INT), CAST(variance_pct AS DOUBLE)
FROM read_files('/Volumes/workspace/fizzco/fizzco_landing/gold/gold_sell_in_vs_sell_out.csv', format => 'csv', header => true);

-- 4. gold_recon_results -------------------------------------------------------------------
CREATE OR REPLACE TABLE gold_recon_results (
  recon_id    STRING COMMENT 'Reconciliation run id, format RECON-####.',
  job_id      STRING COMMENT 'Pipeline job id that ran the reconciliation, format JOB-####.',
  feed        STRING COMMENT 'Data feed that was reconciled: sell_in, sell_out, inventory or promo.',
  recon_date  DATE   COMMENT 'Cut-off date of the reconciliation (inclusive).',
  source_rows INT    COMMENT 'Rows in the source (raw) data up to and including the cut-off date.',
  trusted_rows INT   COMMENT 'Rows in the trusted table up to and including the cut-off date.',
  diff_rows   INT    COMMENT 'source_rows minus trusted_rows. 0 means nothing was lost.',
  status      STRING COMMENT 'MATCH if diff_rows is 0, otherwise MISMATCH.',
  note        STRING COMMENT 'Free-text explanation, filled for mismatches and reruns.'
) COMMENT 'One row per reconciliation run between raw and trusted tables, including the 31 March 2026 sell_in mismatch and its rerun. Synthetic data.';

INSERT INTO gold_recon_results
SELECT recon_id, job_id, feed, CAST(recon_date AS DATE), CAST(source_rows AS INT),
       CAST(trusted_rows AS INT), CAST(diff_rows AS INT), status, note
FROM read_files('/Volumes/workspace/fizzco/fizzco_landing/gold/gold_recon_results.csv', format => 'csv', header => true);

-- 5. gold_promo_performance ---------------------------------------------------------------
CREATE OR REPLACE TABLE gold_promo_performance (
  promo_id          STRING COMMENT 'Promotion id, format PROMO-2026-####.',
  sku               STRING COMMENT 'Product on promotion. Joins to dim_product.sku.',
  retailer_id       STRING COMMENT 'Retailer running the promotion. Joins to dim_retailer.retailer_id.',
  region            STRING COMMENT 'Sales region of the retailer: East or West.',
  start_date        DATE   COMMENT 'First day of the promotion.',
  end_date          DATE   COMMENT 'Last day of the promotion.',
  discount_pct      INT    COMMENT 'Shelf discount during the promotion, in percent (5, 10, 15 or 20).',
  promo_days        INT    COMMENT 'Length of the promotion in days: end_date minus start_date.',
  baseline_units    INT    COMMENT 'Units expected over the promotion period without the promotion.',
  promo_units       INT    COMMENT 'Units actually sold during the promotion.',
  incremental_units INT    COMMENT 'promo_units minus baseline_units: the extra units the promotion sold.',
  uplift_pct        DOUBLE COMMENT 'incremental_units as a percentage of baseline_units.',
  promo_cost        DOUBLE COMMENT 'Cost of the discount: promo_units x list price x discount_pct / 100.'
) COMMENT 'One row per promotion with baseline, actual units, uplift and discount cost. Synthetic data, Q1 2026.';

INSERT INTO gold_promo_performance
SELECT promo_id, sku, retailer_id, region, CAST(start_date AS DATE), CAST(end_date AS DATE),
       CAST(discount_pct AS INT), CAST(promo_days AS INT), CAST(baseline_units AS INT),
       CAST(promo_units AS INT), CAST(incremental_units AS INT), CAST(uplift_pct AS DOUBLE),
       CAST(promo_cost AS DOUBLE)
FROM read_files('/Volumes/workspace/fizzco/fizzco_landing/gold/gold_promo_performance.csv', format => 'csv', header => true);

-- 6. Verification: compare with the expected values --------------------------------------
-- Expected: dim_retailer 10, dim_product 8, gold_sell_in_vs_sell_out 68, gold_recon_results 13,
--           gold_promo_performance 12; sell-in units 13179 and sell-in net amount 22356.54.
SELECT 'dim_retailer' AS table_name, COUNT(*) AS row_count FROM dim_retailer
UNION ALL SELECT 'dim_product', COUNT(*) FROM dim_product
UNION ALL SELECT 'gold_sell_in_vs_sell_out', COUNT(*) FROM gold_sell_in_vs_sell_out
UNION ALL SELECT 'gold_recon_results', COUNT(*) FROM gold_recon_results
UNION ALL SELECT 'gold_promo_performance', COUNT(*) FROM gold_promo_performance;

SELECT SUM(sell_in_units) AS sell_in_units, ROUND(SUM(sell_in_net_amount), 2) AS sell_in_net_amount
FROM gold_sell_in_vs_sell_out;
