# Genie space setup: Retail Sales & Promotions Analytics

Synthetic data only. Catalog `workspace`, schema `fizzco`.

## Scope decision: which tables go in the space

| Table | In the space? | Why |
|---|---|---|
| `gold_sell_in_vs_sell_out` | Yes | Core question set: what we shipped vs what shoppers bought, by region, retailer and product |
| `gold_promo_performance` | Yes | Analysts ask about promotion uplift and cost |
| `dim_retailer` | Yes | Retailer names, region and channel for joins |
| `dim_product` | Yes | Product names and categories for joins |
| `gold_recon_results` | **No** | A data-quality table for engineers and support. Analysts do not need it, and extra tables are the main cause of wrong Genie answers. It is reached later through a UC function (scenario 6.1). |
| `trusted_*` and raw tables | **No** | Not curated for business use |

## General instructions (paste into the space's instructions)

```text
You answer questions for Fizzco commercial analysts. All data is synthetic and covers 2026 Q1.
Sell-in means units and value Fizzco shipped and invoiced to retailers. Sell-out means units and value retailers sold to shoppers.
Regions are East and West. Weeks start on Monday (column week_start).
Money columns are in currency units, rounded to 2 decimals. Percentages are shown as numbers such as 12.5, not 0.125.
Always join retailer_id to dim_retailer and sku to dim_product when the answer needs names.
If a question cannot be answered from these tables, say so instead of guessing.
```

Note: deliberately **no** definition of "net sales" or "variance" here. Scenario 2.2 tests those two terms.

## Business-term instructions (the 5 sample queries)

| # | Term | Definition used | Sample question | Where the SQL is |
|---|---|---|---|---|
| 1 | Net sell-in sales | `sell_in_net_amount`: invoiced value after discounts (gross minus discount) | What were net sell-in sales by region? | `sample_questions.sql` Q1 |
| 2 | Sell-through rate | Total sell-out units divided by total sell-in units, as a percentage | What is the sell-through rate by retailer? | Q2 |
| 3 | Unit gap | `sell_in_units` minus `sell_out_units` (positive means more shipped than sold) | Which products had the largest gap between units shipped and units sold? | Q3 |
| 4 | Promotion uplift | `uplift_pct`: incremental units as a percentage of baseline units | Which promotions had the highest uplift? | Q4 |
| 5 | Promo cost per extra unit | `promo_cost` divided by `incremental_units` | Which promotions cost the most per extra unit sold? | Q5 |

Expected results of every query: `sample_questions_expected.txt` (independently computed).

## Steps that must be done in the Databricks UI

1. Create the Genie space and add the four tables above.
2. Paste the general instructions.
3. Add the five questions as example SQL queries (title = the sample question, SQL = the matching block in `sample_questions.sql`).
4. Ask the five questions in the space and compare each answer with `sample_questions_expected.txt`.
