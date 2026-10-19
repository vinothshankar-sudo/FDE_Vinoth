# Root-cause note: scenario 2.2

| Item | Detail |
|---|---|
| Question (never reworded) | What were net sales by region? |
| Wrong answer | West 15,437.84; East 12,848.45 |
| Right answer (Fizzco definition) | West 12,463.04; East 9,893.50 |
| Column Genie used | `net_sales` in `workspace.fizzco.legacy_sales` (shopper sales at shelf price) |
| Column it should have used | `invoiced_amount` (invoiced value after discounts) |
| Root cause | The table had no comments and no instructions, and a column was named `net_sales` while holding a different measure than the business term "net sales". Genie matched the words in the question to the column name. |
| Fix (metadata, not wording) | Column and table comments in Unity Catalog; a general instruction defining net sales and when to use `net_sales`; an SQL expression `fizzco_net_sales`; an example query for net sales by month |
| Result | Same question now returns West 12,463.04 and East 9,893.50 from `SUM(invoiced_amount)` |
