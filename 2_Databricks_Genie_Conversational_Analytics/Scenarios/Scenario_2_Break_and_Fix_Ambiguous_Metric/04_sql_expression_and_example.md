# Extra fixes in the Genie space (Configure tab)

Do these after the comments and the instruction. The measure is called `fizzco_net_sales`, not `net_sales`, because the legacy column is already called `net_sales`.

## SQL expression (Configure > Instructions > SQL expressions, type: Measure)

| Field | Value |
|---|---|
| Name | `fizzco_net_sales` |
| Expression | `SUM(invoiced_amount)` |
| Synonyms | net sales, sales, invoiced sales |
| Description | Fizzco net sales: value invoiced to retailers after discounts. Not shopper sales. |

## Example SQL query (Configure > Examples)

Title: `What were net sales by month?`

```sql
SELECT date_trunc('MONTH', week_start) AS month,
       ROUND(SUM(invoiced_amount), 2) AS net_sales
FROM workspace.fizzco.legacy_sales
GROUP BY date_trunc('MONTH', week_start)
ORDER BY month;
```
