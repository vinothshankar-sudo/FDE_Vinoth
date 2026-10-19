-- Scenario 2.1: five sample questions with the CORRECT SQL (Fizzco, synthetic data).
-- Each query is verified against the gold CSVs; expected output is in sample_questions_expected.txt.

-- Q1. What were net sell-in sales by region?
-- Definition: net sell-in sales = sell_in_net_amount = invoiced value after discounts (gross minus discount).
SELECT region, ROUND(SUM(sell_in_net_amount), 2) AS net_sell_in_sales
FROM workspace.fizzco.gold_sell_in_vs_sell_out
GROUP BY region
ORDER BY net_sell_in_sales DESC;

-- Q2. What is the sell-through rate by retailer?
-- Definition: sell-through rate = total sell-out units divided by total sell-in units, as a percentage.
SELECT r.retailer_name, r.region,
       SUM(g.sell_in_units) AS sell_in_units,
       SUM(g.sell_out_units) AS sell_out_units,
       ROUND(100.0 * SUM(g.sell_out_units) / SUM(g.sell_in_units), 1) AS sell_through_pct
FROM workspace.fizzco.gold_sell_in_vs_sell_out g
JOIN workspace.fizzco.dim_retailer r ON g.retailer_id = r.retailer_id
GROUP BY r.retailer_name, r.region
HAVING SUM(g.sell_in_units) > 0
ORDER BY sell_through_pct DESC;

-- Q3. Which products had the largest gap between units shipped and units sold?
-- Definition: gap = sell_in_units minus sell_out_units (positive means more shipped than sold).
SELECT p.product_name, p.category,
       SUM(g.sell_in_units) AS units_shipped,
       SUM(g.sell_out_units) AS units_sold,
       SUM(g.variance_units) AS unit_gap
FROM workspace.fizzco.gold_sell_in_vs_sell_out g
JOIN workspace.fizzco.dim_product p ON g.sku = p.sku
GROUP BY p.product_name, p.category
ORDER BY unit_gap DESC;

-- Q4. Which promotions had the highest uplift?
-- Definition: uplift = incremental units as a percentage of baseline units (uplift_pct).
SELECT promo_id, sku, region, discount_pct, baseline_units, promo_units, incremental_units, uplift_pct, promo_cost
FROM workspace.fizzco.gold_promo_performance
ORDER BY uplift_pct DESC
LIMIT 5;

-- Q5. Which promotions cost the most per extra unit sold?
-- Definition: promo cost per extra unit = promo_cost divided by incremental_units (units sold above baseline).
SELECT promo_id, sku, region, discount_pct, incremental_units, promo_cost,
       ROUND(promo_cost / incremental_units, 2) AS promo_cost_per_extra_unit
FROM workspace.fizzco.gold_promo_performance
WHERE incremental_units > 0
ORDER BY promo_cost_per_extra_unit DESC
LIMIT 5;
