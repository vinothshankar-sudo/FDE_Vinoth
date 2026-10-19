-- Scenario 5.4: the row filter is the one from Scenario 2.3. Nothing new is created for this scenario.
-- 1. Re-apply it: run 2_Databricks_Genie_Conversational_Analytics/Scenarios/Scenario_3_Governance_Check_Row_Level_Access/01_row_filter_template.sql
--    in the SQL Editor after replacing <WEST_MANAGER_EMAIL> and <EAST_MANAGER_EMAIL> with the two real sign-in emails
--    (for your own run only; never commit the real emails).
-- 2. Check as yourself (should show only your region):
SELECT current_user() AS me, region, COUNT(*) AS row_count
FROM workspace.fizzco.gold_sell_in_vs_sell_out
GROUP BY region;
-- 3. After the two-user test is captured, remove the filters again (same folder, 03_rollback.sql):
--    ALTER TABLE workspace.fizzco.gold_sell_in_vs_sell_out DROP ROW FILTER;
--    ALTER TABLE workspace.fizzco.gold_promo_performance   DROP ROW FILTER;
