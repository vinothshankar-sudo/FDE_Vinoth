# Databricks notebook source
# Raw -> Trusted: sell_in. Writes net_amount = gross_amount - discount_amount.
import csv
from config import RAW_DIR, TRUSTED_DIR

def Transform(inPath, outPath):
    rows = []
    try:
        with open(inPath) as f:
            for r in csv.DictReader(f):
                r["net_amount"] = round(float(r["gross_amount"]) - float(r["discount_amount"]), 2)
                rows.append(r)
    except:
        print("something failed")
    with open(outPath, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("done", len(rows))

if __name__ == "__main__":
    Transform(RAW_DIR + "/sell_in.csv", TRUSTED_DIR + "/trusted_sell_in.csv")
