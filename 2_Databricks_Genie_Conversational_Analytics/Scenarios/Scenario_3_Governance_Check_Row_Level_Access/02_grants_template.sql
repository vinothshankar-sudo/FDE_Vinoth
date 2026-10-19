-- Scenario 2.3: give the second identity read access (run as the table owner).
-- Replace <EAST_MANAGER_EMAIL>. The Genie space itself is shared from the space's Share button (Can run).
GRANT USE CATALOG ON CATALOG workspace TO `<EAST_MANAGER_EMAIL>`;
GRANT USE SCHEMA  ON SCHEMA  workspace.fizzco TO `<EAST_MANAGER_EMAIL>`;
GRANT SELECT ON TABLE workspace.fizzco.gold_sell_in_vs_sell_out TO `<EAST_MANAGER_EMAIL>`;
GRANT SELECT ON TABLE workspace.fizzco.gold_promo_performance   TO `<EAST_MANAGER_EMAIL>`;
GRANT SELECT ON TABLE workspace.fizzco.dim_retailer TO `<EAST_MANAGER_EMAIL>`;
GRANT SELECT ON TABLE workspace.fizzco.dim_product  TO `<EAST_MANAGER_EMAIL>`;
