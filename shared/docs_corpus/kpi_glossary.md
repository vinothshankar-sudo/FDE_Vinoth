---
doc_id: GLO-KPI-001
title: KPI glossary
doc_type: glossary
feed: all
owner: Fizzco Commercial Analytics (fictional team)
last_reviewed: 2026-04-02
---
# KPI glossary

## Sell-in and sell-out
**Sell-in** is what Fizzco shipped and invoiced to retailers. **Sell-out** is what retailers sold to shoppers, measured from scan data. Sell-in is recorded in the sell_in feed and sell-out in the sell_out feed. A week starts on Monday, and the column `week_start` holds that Monday.

## Net sell-in sales
Net sell-in sales is the invoiced value to retailers after discounts: gross amount minus discount amount. In the gold table it is the column `sell_in_net_amount`; in the trusted sell_in table it is `net_amount`. Always say "net sell-in sales". The phrase "net sales" alone is ambiguous.

## Why "net sales" is ambiguous
Some legacy tables have a column called `net_sales` that holds shopper sales (what retailers sold to shoppers at shelf price), which is sell-out value and not Fizzco's net sales. Fizzco's definition of net sales is the value invoiced to retailers after discounts. A question about net sales must be answered with the invoiced value, not with the column that happens to be called net_sales. Do not compare the two values with each other as if they were on the same price basis.

## Shopper sales
Shopper sales is the value of units that retailers sold to shoppers at shelf price. In the gold table it is `sell_out_amount`.

## Variance
Two kinds of variance are used. **Unit variance** (`variance_units`) is sell-in units minus sell-out units; positive means more units were shipped than sold. **Variance percentage** (`variance_pct`) is unit variance as a percentage of sell-in units; it is empty when there was no sell-in in the week. When a total is needed across many rows, divide the summed unit variance by the summed sell-in units; do not average the row percentages.

## Sell-through rate
Sell-through rate is total sell-out units divided by total sell-in units, as a percentage with one decimal. A higher rate means shelves are emptying faster than they are being filled.

## Promotion uplift and cost
**Baseline units** are the units expected over the promotion period without the promotion. **Incremental units** are promo units minus baseline units. **Uplift percentage** (`uplift_pct`) is incremental units as a percentage of baseline units. **Promo cost** is promo units multiplied by list price multiplied by the discount percentage divided by 100. **Promo cost per extra unit** is promo cost divided by incremental units.

## Reconciliation terms
**Source rows** are the rows in the raw data for the window; **trusted rows** are the rows in the trusted table for the same window; **difference** is source minus trusted. Status is **MATCH** when the difference is zero and **MISMATCH** otherwise.
