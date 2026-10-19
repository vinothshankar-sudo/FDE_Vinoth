-- Scenario 2.2 fix: put the business meaning into Unity Catalog metadata (not into the question).
ALTER TABLE workspace.fizzco.legacy_sales ALTER COLUMN net_sales
  COMMENT 'Legacy name. Value of sales to shoppers at shelf price (retailer scan data). It is NOT Fizzco net sales. Use only for shopper sales.';
ALTER TABLE workspace.fizzco.legacy_sales ALTER COLUMN invoiced_amount
  COMMENT 'Fizzco net sales: value invoiced to the retailer after discounts (gross minus discount). Use this column for any question about net sales or sales.';
ALTER TABLE workspace.fizzco.legacy_sales ALTER COLUMN units_shipped
  COMMENT 'Units Fizzco invoiced to the retailer that week (sell-in).';
ALTER TABLE workspace.fizzco.legacy_sales ALTER COLUMN units_sold
  COMMENT 'Units the retailer sold to shoppers that week (sell-out).';
COMMENT ON TABLE workspace.fizzco.legacy_sales IS
  'Weekly sales by retailer and product. Synthetic data, 2026 Q1. Column net_sales is a legacy name for shopper sales; Fizzco net sales is invoiced_amount.';
