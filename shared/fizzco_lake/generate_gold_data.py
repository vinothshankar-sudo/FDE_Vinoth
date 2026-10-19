"""Generate the synthetic dimension, sell-out and gold tables for Module 2 onwards.

Fully synthetic and seeded (SEED = 42). Reads the existing trusted CSVs, never edits them.
Run from shared/fizzco_lake:  python3 generate_gold_data.py
Writes to data/gold/ (CSV, header row, ISO dates).
"""
import csv
import logging
import random
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

SEED = 42
BASE_DIR = Path(__file__).resolve().parent
TRUSTED_DIR = BASE_DIR / "data" / "trusted"
GOLD_DIR = BASE_DIR / "data" / "gold"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s - %(message)s"
LOGGER = logging.getLogger("generate_gold_data")

# Retailer to region. East and West alternate so both regions have data.
RETAILERS = [
    ("R001", "Brightmart", "East", "Supermarket"),
    ("R002", "Cornerbay", "West", "Convenience"),
    ("R003", "Daily Fresh", "East", "Supermarket"),
    ("R004", "Evergreen Foods", "West", "Supermarket"),
    ("R005", "Fieldstone", "East", "Convenience"),
    ("R006", "Greenleaf", "West", "Discount"),
    ("R007", "Harbor Grocers", "East", "Supermarket"),
    ("R008", "Ironwood Market", "West", "Convenience"),
    ("R009", "Juniper Stores", "East", "Discount"),
    ("R010", "Kestrel Mart", "West", "Supermarket"),
]
REGION_BY_RETAILER = {r[0]: r[2] for r in RETAILERS}

# sku, product name, category, pack size, list price per unit
PRODUCTS = [
    ("FZ-COLA-330", "Fizzco Cola 330ml can", "Beverage", "330 ml", 1.20),
    ("FZ-COLA-500", "Fizzco Cola 500ml bottle", "Beverage", "500 ml", 1.80),
    ("FZ-LIME-330", "Fizzco Lime Soda 330ml can", "Beverage", "330 ml", 1.20),
    ("FZ-ORNG-500", "Fizzco Orange 500ml bottle", "Beverage", "500 ml", 1.80),
    ("FZ-CHIP-SALT", "Fizzco Salted Chips 150g", "Snack", "150 g", 2.40),
    ("FZ-CHIP-BBQ", "Fizzco BBQ Chips 150g", "Snack", "150 g", 2.40),
    ("FZ-BISC-CHOC", "Fizzco Choc Biscuits 200g", "Snack", "200 g", 2.10),
    ("FZ-BISC-MARI", "Fizzco Marie Biscuits 200g", "Snack", "200 g", 1.90),
]
PRICE_BY_SKU = {p[0]: p[4] for p in PRODUCTS}

FEEDS = ["sell_in", "sell_out", "inventory", "promo"]
FEED_DATE_COLUMN = {"sell_in": "order_date", "sell_out": "sale_date",
                    "inventory": "snapshot_date", "promo": "start_date"}
MONTH_ENDS = [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]
INCIDENT_DATE = date(2026, 3, 31)


def monday_of(day):
    return day - timedelta(days=day.weekday())


def read_csv(path):
    try:
        with open(path, newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    LOGGER.info("wrote %d rows to %s", len(rows), path)


def build_dim_tables():
    write_csv(GOLD_DIR / "dim_retailer.csv",
              ["retailer_id", "retailer_name", "region", "channel"], RETAILERS)
    write_csv(GOLD_DIR / "dim_product.csv",
              ["sku", "product_name", "category", "pack_size", "list_price"], PRODUCTS)


def build_sell_out(rng, sell_in):
    """Scan-level sales: roughly 70 to 105 percent of what each retailer bought that week."""
    rows = []
    for order in sell_in:
        order_day = date.fromisoformat(order["order_date"])
        units_in = int(order["units"])
        share = rng.uniform(0.70, 1.05)
        units_out = max(1, round(units_in * share))
        # Split the week's sales over two scan days inside the same Monday-to-Sunday week.
        week_start = monday_of(order_day)
        first = round(units_out * rng.uniform(0.4, 0.6))
        for part, sale_day in ((first, week_start + timedelta(days=rng.randint(0, 3))),
                               (units_out - first, week_start + timedelta(days=rng.randint(4, 6)))):
            if part <= 0:
                continue
            retail_price = round(PRICE_BY_SKU[order["sku"]] * rng.uniform(1.25, 1.45), 2)
            rows.append([sale_day.isoformat(), order["retailer_id"], order["sku"],
                         part, round(part * retail_price, 2)])
    # A few sell-out rows with no matching sell-in week (sold from older stock).
    for _ in range(6):
        retailer = rng.choice(RETAILERS)[0]
        sku = rng.choice(PRODUCTS)[0]
        sale_day = date(2026, 1, 5) + timedelta(days=rng.randint(0, 80))
        units = rng.randint(5, 60)
        rows.append([sale_day.isoformat(), retailer, sku, units,
                     round(units * PRICE_BY_SKU[sku] * 1.35, 2)])
    rows.sort()
    write_csv(TRUSTED_DIR / "trusted_sell_out.csv",
              ["sale_date", "retailer_id", "sku", "units", "sale_amount"], rows)
    return rows


def build_sell_in_vs_sell_out(sell_in, sell_out):
    keyed = defaultdict(lambda: {"in_units": 0, "in_gross": 0.0, "in_disc": 0.0,
                                 "out_units": 0, "out_amount": 0.0})
    for row in sell_in:
        key = (monday_of(date.fromisoformat(row["order_date"])), row["retailer_id"], row["sku"])
        keyed[key]["in_units"] += int(row["units"])
        keyed[key]["in_gross"] += float(row["gross_amount"])
        keyed[key]["in_disc"] += float(row["discount_amount"])
    for row in sell_out:
        key = (monday_of(date.fromisoformat(row[0])), row[1], row[2])
        keyed[key]["out_units"] += int(row[3])
        keyed[key]["out_amount"] += float(row[4])
    out = []
    for (week, retailer, sku), v in sorted(keyed.items()):
        variance_units = v["in_units"] - v["out_units"]
        variance_pct = round(100.0 * variance_units / v["in_units"], 2) if v["in_units"] else ""
        out.append([week.isoformat(), REGION_BY_RETAILER[retailer], retailer, sku,
                    v["in_units"], round(v["in_gross"], 2), round(v["in_disc"], 2),
                    round(v["in_gross"] - v["in_disc"], 2),
                    v["out_units"], round(v["out_amount"], 2),
                    variance_units, variance_pct])
    write_csv(GOLD_DIR / "gold_sell_in_vs_sell_out.csv",
              ["week_start", "region", "retailer_id", "sku", "sell_in_units",
               "sell_in_gross_amount", "sell_in_discount_amount", "sell_in_net_amount",
               "sell_out_units", "sell_out_amount", "variance_units", "variance_pct"], out)
    return out


def count_up_to(rows, column, cutoff):
    return sum(1 for r in rows if r[column] <= cutoff.isoformat())


def build_recon_results(feed_rows):
    rows, recon_n, job_n = [], 0, 40
    for month_end in MONTH_ENDS:
        for feed in FEEDS:
            source = count_up_to(feed_rows[feed], FEED_DATE_COLUMN[feed], month_end)
            trusted, status, note = source, "MATCH", ""
            if feed == "sell_in" and month_end == INCIDENT_DATE:
                trusted, status = source - 3, "MISMATCH"
                note = "date filter excluded the end date; 3 rows dated 2026-03-31 not counted"
            recon_n, job_n = recon_n + 1, job_n + 1
            rows.append([f"RECON-{recon_n:04d}", f"JOB-{job_n:04d}", feed,
                         month_end.isoformat(), source, trusted, source - trusted, status, note])
    source = count_up_to(feed_rows["sell_in"], "order_date", INCIDENT_DATE)
    recon_n, job_n = recon_n + 1, job_n + 1
    rows.append([f"RECON-{recon_n:04d}", f"JOB-{job_n:04d}", "sell_in", INCIDENT_DATE.isoformat(),
                 source, source, 0, "MATCH", "rerun after the end-date fix"])
    write_csv(GOLD_DIR / "gold_recon_results.csv",
              ["recon_id", "job_id", "feed", "recon_date", "source_rows", "trusted_rows",
               "diff_rows", "status", "note"], rows)
    return rows


def build_promo_performance(rng, promos):
    rows = []
    for promo in promos:
        start = date.fromisoformat(promo["start_date"])
        end = date.fromisoformat(promo["end_date"])
        days = (end - start).days
        baseline = round(rng.uniform(15, 55) * days)
        uplift = round(rng.uniform(5, 60), 1)
        promo_units = round(baseline * (1 + uplift / 100))
        discount = float(promo["discount_pct"])
        cost = round(promo_units * PRICE_BY_SKU[promo["sku"]] * discount / 100, 2)
        rows.append([promo["promo_id"], promo["sku"], promo["retailer_id"],
                     REGION_BY_RETAILER[promo["retailer_id"]], promo["start_date"],
                     promo["end_date"], int(discount), days, baseline, promo_units,
                     promo_units - baseline, uplift, cost])
    write_csv(GOLD_DIR / "gold_promo_performance.csv",
              ["promo_id", "sku", "retailer_id", "region", "start_date", "end_date",
               "discount_pct", "promo_days", "baseline_units", "promo_units",
               "incremental_units", "uplift_pct", "promo_cost"], rows)
    return rows


def main():
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, stream=sys.stderr)
    LOGGER.info("step start: generate synthetic gold data, SEED=%d", SEED)
    rng = random.Random(SEED)
    try:
        sell_in = read_csv(TRUSTED_DIR / "trusted_sell_in.csv")
        inventory = read_csv(TRUSTED_DIR / "trusted_inventory.csv")
        promos = read_csv(TRUSTED_DIR / "trusted_promo.csv")
    except ValueError as exc:
        LOGGER.error("%s", exc)
        return 1
    build_dim_tables()
    sell_out = build_sell_out(rng, sell_in)
    build_sell_in_vs_sell_out(sell_in, sell_out)
    feed_rows = {
        "sell_in": sell_in,
        "sell_out": [{"sale_date": r[0]} for r in sell_out],
        "inventory": inventory,
        "promo": promos,
    }
    build_recon_results(feed_rows)
    build_promo_performance(rng, promos)
    LOGGER.info("step end: gold data generated in %s", GOLD_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
