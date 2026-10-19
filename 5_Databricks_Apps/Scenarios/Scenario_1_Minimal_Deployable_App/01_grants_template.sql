-- Scenario 5.1: let the app's service principal read the recon table. Run in the SQL Editor as the table owner.
-- Replace <APP_SERVICE_PRINCIPAL> with the name shown on the app page (Authorization / Service principal).
-- Do not paste emails or tokens into this file; commit it with the placeholder.
GRANT USE CATALOG ON CATALOG workspace TO `<APP_SERVICE_PRINCIPAL>`;
GRANT USE SCHEMA ON SCHEMA workspace.fizzco TO `<APP_SERVICE_PRINCIPAL>`;
GRANT SELECT ON TABLE workspace.fizzco.gold_recon_results TO `<APP_SERVICE_PRINCIPAL>`;
-- Check:
SHOW GRANTS ON TABLE workspace.fizzco.gold_recon_results;
