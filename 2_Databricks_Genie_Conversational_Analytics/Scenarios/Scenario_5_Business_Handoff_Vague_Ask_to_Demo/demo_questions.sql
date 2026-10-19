-- Scenario 2.5: demo questions with the CORRECT SQL (Fizzco, synthetic data, 2025-12-29 to 2026-03-30).
-- Definitions: see scope_decisions.md. Expected output: demo_questions_expected.txt (computed independently).
-- Tables in the demo space: workspace.fizzco.gold_sell_in_vs_sell_out, workspace.fizzco.dim_retailer.

-- D1. How are our regions performing?   (added to the space as example query 1)
SELECT g.region,
       ROUND(SUM(g.sell_in_net_amount), 2) AS net_sell_in_sales,
       ROUND(SUM(g.sell_out_amount), 2)    AS shopper_sales,
       SUM(g.sell_in_units)                AS units_shipped,
       SUM(g.sell_out_units)               AS units_sold,
       ROUND(100.0 * SUM(g.sell_out_units) / SUM(g.sell_in_units), 1) AS sell_through_pct
FROM workspace.fizzco.gold_sell_in_vs_sell_out g
GROUP BY g.region
ORDER BY net_sell_in_sales DESC;

-- D2. Which retail channel is performing best?   (NOT in the space as an example: tests generalisation)
SELECT r.channel,
       SUM(g.sell_in_units)  AS units_shipped,
       SUM(g.sell_out_units) AS units_sold,
       ROUND(100.0 * SUM(g.sell_out_units) / SUM(g.sell_in_units), 1) AS sell_through_pct
FROM workspace.fizzco.gold_sell_in_vs_sell_out g
JOIN workspace.fizzco.dim_retailer r ON g.retailer_id = r.retailer_id
GROUP BY r.channel
ORDER BY sell_through_pct DESC;

-- D3. Which retailers are underperforming?   (added to the space as example query 2)
-- Definition: underperforming = sell-through % below the overall sell-through % of all retailers.
WITH by_retailer AS (
  SELECT r.retailer_name, r.region, r.channel,
         SUM(g.sell_in_units)  AS units_shipped,
         SUM(g.sell_out_units) AS units_sold,
         100.0 * SUM(g.sell_out_units) / SUM(g.sell_in_units) AS sell_through
  FROM workspace.fizzco.gold_sell_in_vs_sell_out g
  JOIN workspace.fizzco.dim_retailer r ON g.retailer_id = r.retailer_id
  GROUP BY r.retailer_name, r.region, r.channel
), overall AS (
  SELECT 100.0 * SUM(sell_out_units) / SUM(sell_in_units) AS sell_through
  FROM workspace.fizzco.gold_sell_in_vs_sell_out
)
SELECT b.retailer_name, b.region, b.channel, b.units_shipped, b.units_sold,
       ROUND(b.sell_through, 1) AS sell_through_pct
FROM by_retailer b CROSS JOIN overall o
WHERE b.sell_through < o.sell_through
ORDER BY b.sell_through ASC;

-- D4. How is performance trending by month?   (NOT in the space as an example)
-- Note: month = month of week_start. 2025-12 holds one week only (week of 2025-12-29), so it is a partial month.
SELECT DATE_FORMAT(g.week_start, 'yyyy-MM') AS month,
       ROUND(SUM(g.sell_in_net_amount), 2) AS net_sell_in_sales,
       SUM(g.sell_in_units)  AS units_shipped,
       SUM(g.sell_out_units) AS units_sold,
       ROUND(100.0 * SUM(g.sell_out_units) / SUM(g.sell_in_units), 1) AS sell_through_pct
FROM workspace.fizzco.gold_sell_in_vs_sell_out g
GROUP BY DATE_FORMAT(g.week_start, 'yyyy-MM')
ORDER BY month;

-- D5. What is our market share versus competitors?   (OUT OF SCOPE: no such data. Genie must say it cannot answer.)
-- No SQL: the correct behaviour is a refusal that names what IS available.
