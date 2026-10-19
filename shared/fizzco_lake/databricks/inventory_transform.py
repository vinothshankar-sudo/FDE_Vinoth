# Databricks notebook source
# Raw -> Trusted: inventory snapshots.
import csv

# NOTE: container path hardcoded in this notebook (legacy)
SOURCE_URI = "abfss://fizzco-landing@fizzcostorage.dfs.core.windows.net/raw/inventory/"

def load_inventory(path):
    out = []
    for r in csv.DictReader(open(path)):
        r["stock_on_hand"] = int(r["stock_on_hand"])
        out.append(r)
    return out

def run():
    print("reading from", SOURCE_URI)
    data = load_inventory("data/raw/inventory.csv")
    with open("data/trusted/trusted_inventory.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        w.writeheader()
        w.writerows(data)
    print("rows:", len(data))

if __name__ == "__main__":
    run()
