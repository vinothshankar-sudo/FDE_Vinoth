-- Scenario 2.2 setup: a "legacy" sales table with a column name that clashes with the business term.
-- Synthetic data only. Run in the Databricks SQL Editor (Serverless Starter Warehouse).
-- The column named net_sales holds SHOPPER sales at shelf price (sell_out_amount).
-- Fizzco Finance defines "net sales" as the invoiced value after discounts (sell_in_net_amount),
-- which lives in the column invoiced_amount. No column or table comments on purpose.

CREATE OR REPLACE TABLE workspace.fizzco.legacy_sales (
  week_start      DATE,
  region          STRING,
  retailer_id     STRING,
  sku             STRING,
  net_sales       DOUBLE,
  invoiced_amount DOUBLE,
  units_shipped   INT,
  units_sold      INT
);

INSERT INTO workspace.fizzco.legacy_sales
SELECT week_start, region, retailer_id, sku,
       sell_out_amount, sell_in_net_amount, sell_in_units, sell_out_units
FROM workspace.fizzco.gold_sell_in_vs_sell_out;

-- Check: expect 68 rows; shopper sales West 15,437.84 / East 12,848.45; invoiced West 12,463.04 / East 9,893.50.
SELECT region, COUNT(*) AS row_count,
       ROUND(SUM(net_sales), 2) AS net_sales_column,
       ROUND(SUM(invoiced_amount), 2) AS invoiced_amount_column
FROM workspace.fizzco.legacy_sales
GROUP BY region ORDER BY region;
