# Genie space setup: Fizzco Market Performance Demo

Synthetic data only. Catalog `workspace`, schema `fizzco`. Table and column comments already exist in Unity Catalog from scenario 2.1 and are reused.

## Steps in the Databricks UI

1. Genie > New > connect data. Add exactly two tables: `workspace.fizzco.gold_sell_in_vs_sell_out` and `workspace.fizzco.dim_retailer`. Use the Serverless Starter Warehouse.
2. Name the space `Fizzco Market Performance Demo`.
3. Configure > Instructions: paste the text below.
4. Configure > Examples (or SQL queries): add D1 and D3 from `demo_questions.sql`. Title = the question, SQL = the block. Do not add D2, D4 or D5.
5. Share: leave private (only you). No sharing is needed for this scenario.

## General instructions (paste into the space)

```text
You answer questions for a Fizzco regional sales director who wants to know how markets are performing. All data is synthetic and covers 14 weeks from 2025-12-29 to 2026-03-30.
"Markets" means Fizzco's own sales regions (East, West), retail channels (Supermarket, Convenience, Discount) and retailers. There is no competitor or market-share data.
Performance is measured mainly by sell-through percentage = 100 * SUM(sell_out_units) / SUM(sell_in_units), shown with one decimal. Net sell-in sales = SUM(sell_in_net_amount), the invoiced value after discounts. Shopper sales = SUM(sell_out_amount). Always say "net sell-in sales", never just "net sales".
An underperforming retailer has a sell-through percentage below the overall sell-through percentage of all retailers.
Month means the month of week_start. 2025-12 contains one week only, so say it is a partial month when it appears.
Join retailer_id to dim_retailer when the answer needs retailer name, region or channel.
Do not subtract net sell-in sales from shopper sales; they are on different price bases.
If a question needs data that is not in these tables (market share, competitors, forecasts, profit), say you cannot answer it, and list what you can answer: sell-through, net sell-in sales and shopper sales by region, channel, retailer and month.
```

## Order of testing

Ask D1 to D5 from `scope_decisions.md`, in that order, in one new chat. After each answer click Show code and compare with `demo_questions_expected.txt`.
