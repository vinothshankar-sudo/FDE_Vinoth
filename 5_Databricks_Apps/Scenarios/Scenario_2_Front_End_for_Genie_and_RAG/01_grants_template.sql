-- Scenario 5.2: the app's service principal also needs to read the tables behind the Genie space.
-- The Genie space "Retail Sales & Promotions Analytics" uses these four tables.
-- Preferred route: Catalog > workspace > fizzco > <table> > Permissions > Grant > pick the app's service principal > SELECT.
-- (Granting by display name in SQL failed in 5.1 with PRINCIPAL_DOES_NOT_EXIST; if you use SQL, use the application ID.)
-- Placeholder only in the repo: <APP_SERVICE_PRINCIPAL_APPLICATION_ID>
GRANT SELECT ON TABLE workspace.fizzco.gold_sell_in_vs_sell_out TO `<APP_SERVICE_PRINCIPAL_APPLICATION_ID>`;
GRANT SELECT ON TABLE workspace.fizzco.gold_promo_performance   TO `<APP_SERVICE_PRINCIPAL_APPLICATION_ID>`;
GRANT SELECT ON TABLE workspace.fizzco.dim_retailer             TO `<APP_SERVICE_PRINCIPAL_APPLICATION_ID>`;
GRANT SELECT ON TABLE workspace.fizzco.dim_product              TO `<APP_SERVICE_PRINCIPAL_APPLICATION_ID>`;
