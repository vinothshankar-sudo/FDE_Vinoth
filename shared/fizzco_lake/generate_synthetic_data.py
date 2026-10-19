"""Generate small, fully synthetic Fizzco raw files. Seeded for reproducibility.
All names, SKUs and numbers are fictional."""
import csv
import random
from datetime import date, timedelta

SEED = 42
random.seed(SEED)

SKUS = ["FZ-COLA-330", "FZ-COLA-500", "FZ-LIME-330", "FZ-ORNG-500",
        "FZ-CHIP-SALT", "FZ-CHIP-BBQ", "FZ-BISC-CHOC", "FZ-BISC-MARI"]
RETAILERS = [f"R{n:03d}" for n in range(1, 11)]
DCS = ["DC-NORTH", "DC-SOUTH", "DC-EAST", "DC-WEST"]


def rand_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))


def write(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    start, end = date(2026, 1, 2), date(2026, 3, 30)
    rows = []
    for _ in range(60):
        units = random.randint(10, 400)
        price = round(random.uniform(0.8, 3.2), 2)
        gross = round(units * price, 2)
        disc = round(gross * random.choice([0, 0, 0.05, 0.1, 0.15]), 2)
        rows.append([rand_date(start, end).isoformat(), random.choice(RETAILERS),
                     random.choice(SKUS), units, gross, disc])
    # Three orders land on the last day of the quarter (used by the recon scenario)
    for _ in range(3):
        units = random.randint(10, 400)
        gross = round(units * 1.5, 2)
        rows.append(["2026-03-31", random.choice(RETAILERS), random.choice(SKUS),
                     units, gross, 0.0])
    rows.sort()
    write("data/raw/sell_in.csv",
          ["order_date", "retailer_id", "sku", "units", "gross_amount", "discount_amount"], rows)

    inv = []
    for _ in range(40):
        inv.append([rand_date(start, date(2026, 3, 31)).isoformat(),
                    random.choice(DCS), random.choice(SKUS), random.randint(0, 5000)])
    inv.sort()
    write("data/raw/inventory.csv", ["snapshot_date", "dc_id", "sku", "stock_on_hand"], inv)

    promo = []
    for n in range(1, 13):
        s = rand_date(date(2026, 1, 5), date(2026, 3, 1))
        promo.append([f"PROMO-2026-{n:04d}", random.choice(SKUS), random.choice(RETAILERS),
                      s.isoformat(), (s + timedelta(days=random.randint(7, 28))).isoformat(),
                      random.choice([5, 10, 15, 20])])
    write("data/raw/promo.csv",
          ["promo_id", "sku", "retailer_id", "start_date", "end_date", "discount_pct"], promo)


if __name__ == "__main__":
    main()
