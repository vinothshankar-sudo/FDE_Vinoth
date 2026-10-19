# Scope decisions: "Show me how markets are performing"

Synthetic data only (Fizzco, 2025-12-29 to 2026-03-30, 14 weeks). The stakeholder is fictional, so the open questions below could not be asked; each one is handled as a stated assumption that a real stakeholder would confirm in the first meeting.

**Bottom line:** the ask was turned into a small Genie space over 2 tables that answers "how are our regions, channels and retailers performing, measured by sell-through and net sell-in sales". Market share and competitor questions are out of scope because the data does not contain them, and the space is set up to say so.

## 1. What the vague ask could mean, and what was chosen

| Word in the ask | Possible meanings | Chosen | Why |
|---|---|---|---|
| "Markets" | (a) Fizzco's sales regions, (b) retail channels, (c) individual retailers, (d) the whole category including competitors | (a) + (b) + (c): East/West, Supermarket/Convenience/Discount, 10 retailers | These are the only market cuts in the data. (d) needs external market data we do not have. |
| "Performing" | Net sell-in sales, shopper sales, sell-through %, growth, profit, promotion return | Primary: sell-through % (units sold to shoppers divided by units shipped). Secondary: net sell-in sales, shopper sales | Sell-through is the one measure that compares markets of different size. No cost data exists, so profit is impossible. |
| Time frame | Latest week, quarter, year on year | Whole period, plus a monthly trend | One quarter of data: no year-on-year comparison is possible. |

## 2. What is in and out

| Item | In the demo space? | Reason |
|---|---|---|
| `gold_sell_in_vs_sell_out` | Yes | Holds every performance measure asked for |
| `dim_retailer` | Yes | Gives retailer name, region and channel |
| `dim_product` | No | Product mix is a second conversation; fewer tables means fewer wrong joins |
| `gold_promo_performance` | No | Promotions answer "did it work?", not "how are markets performing?" |
| `gold_recon_results` | No | Data-quality table for engineers, not for a commercial audience |
| Market share, competitors, forecasts, profit | No | Not in the data. The space instructions tell Genie to say so. |

## 3. Definitions fixed up front (lesson from 2.2)

| Term | Definition in the space |
|---|---|
| Net sell-in sales | `SUM(sell_in_net_amount)`: invoiced value to retailers after discounts. Always say "net sell-in sales", never just "net sales". |
| Shopper sales | `SUM(sell_out_amount)`: what retailers sold to shoppers, at shopper prices |
| Sell-through % | `100 * SUM(sell_out_units) / SUM(sell_in_units)`, one decimal |
| Underperforming retailer | Sell-through % below the overall sell-through % of all retailers |
| Month | Month of `week_start`. December 2025 holds one week only (the week of 2025-12-29), so it is a partial month. |

Net sell-in sales and shopper sales are on different price bases (invoiced after discount versus shopper prices), so the demo never subtracts one from the other.

## 4. Questions that would be asked of a real stakeholder (kept as assumptions here)

| # | Question | Assumption used |
|---|---|---|
| 1 | Does "markets" include competitors? | No |
| 2 | Is sell-through the performance measure you care about? | Yes, with net sell-in sales next to it |
| 3 | Which period matters? | The full 14 weeks |

## 5. How the demo is tested

Four in-scope questions and one out-of-scope question. Two in-scope questions (D1, D3) are added to the space as example queries; two (D2, D4) are not, to see whether Genie answers correctly without a matching example. Correct SQL and expected results: `demo_questions.sql`, `demo_questions_expected.txt`.

| # | Question | In space as example? | What a correct answer looks like |
|---|---|---|---|
| D1 | How are our regions performing? | Yes | West 12,463.04 / East 9,893.50 net sell-in; both 88.9% sell-through |
| D2 | Which retail channel is performing best? | No | Discount 94.2%, Convenience 91.0%, Supermarket 85.9% |
| D3 | Which retailers are underperforming? | Yes | Kestrel Mart 77.0%, Daily Fresh 80.6%, Evergreen Foods 87.5% |
| D4 | How is performance trending by month? | No | 2025-12 92.4% (partial), 2026-01 88.2%, 2026-02 86.3%, 2026-03 91.1% |
| D5 | What is our market share versus competitors? | No | Genie says it cannot answer from these tables and names what it can answer |

## 6. What the demo tells the stakeholder

Regions look the same on sell-through (both 88.9%); the gap is by channel and retailer. All three underperforming retailers are supermarkets, and supermarkets have the lowest channel sell-through (85.9%). That is the finding to open the conversation with.

## 7. Time box

| Step | Planned | Actual (fill in from your clock) |
|---|---|---|
| Write scope decisions | 15 min | |
| Create the space, add 2 tables, paste instructions | 10 min | |
| Add 2 example queries | 5 min | |
| Ask the 5 questions, compare with the key | 15 min | |
| Screenshots and README | 10 min | |
| **Total** | **55 min** | **20 min** (author's total; per-step split not recorded) |
