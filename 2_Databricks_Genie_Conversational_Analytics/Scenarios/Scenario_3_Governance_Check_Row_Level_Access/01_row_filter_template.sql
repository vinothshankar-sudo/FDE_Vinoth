-- Scenario 2.3: row-level access by region (Fizzco, synthetic data).
-- TEMPLATE: replace <WEST_MANAGER_EMAIL> and <EAST_MANAGER_EMAIL> with the two sign-in emails
-- BEFORE running in the SQL Editor. Do not commit the real emails to the repo.

CREATE OR REPLACE FUNCTION workspace.fizzco.region_row_filter(row_region STRING)
RETURN CASE
  WHEN current_user() = '<WEST_MANAGER_EMAIL>' THEN row_region = 'West'
  WHEN current_user() = '<EAST_MANAGER_EMAIL>' THEN row_region = 'East'
  ELSE FALSE
END;

ALTER TABLE workspace.fizzco.gold_sell_in_vs_sell_out SET ROW FILTER workspace.fizzco.region_row_filter ON (region);
ALTER TABLE workspace.fizzco.gold_promo_performance   SET ROW FILTER workspace.fizzco.region_row_filter ON (region);

-- Test as each user (SQL Editor): the first must show only West, the second only East.
SELECT current_user() AS me, region, COUNT(*) AS row_count, ROUND(SUM(sell_in_net_amount), 2) AS net_sell_in
FROM workspace.fizzco.gold_sell_in_vs_sell_out
GROUP BY region;
