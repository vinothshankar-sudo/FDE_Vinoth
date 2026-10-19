-- Scenario 2.3 rollback: remove the row filters after the evidence is captured,
-- so later modules see all regions again.
ALTER TABLE workspace.fizzco.gold_sell_in_vs_sell_out DROP ROW FILTER;
ALTER TABLE workspace.fizzco.gold_promo_performance   DROP ROW FILTER;
