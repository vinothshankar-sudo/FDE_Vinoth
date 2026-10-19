# Databricks notebook source
# Raw -> Trusted: promotions. Adds promo_days = end_date - start_date.
import csv
from datetime import date
from config import RAW_DIR, TRUSTED_DIR, CONTAINER

def PromoTransform():
    out = []
    for r in csv.DictReader(open(f"{RAW_DIR}/promo.csv")):
        s, e = date.fromisoformat(r["start_date"]), date.fromisoformat(r["end_date"])
        r["promo_days"] = (e - s).days
        out.append(r)
    with open(f"{TRUSTED_DIR}/trusted_promo.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print("container:", CONTAINER, "rows:", len(out))

if __name__ == "__main__":
    PromoTransform()
