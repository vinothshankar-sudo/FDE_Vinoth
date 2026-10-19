# Reconciliation: compare raw vs trusted row counts for a date window.
import csv
import sys
from datetime import date


def count_source_rows(path, date_col, start, end):
    n = 0
    for r in csv.DictReader(open(path)):
        d = date.fromisoformat(r[date_col])
        if start <= d <= end:
            n += 1
    return n


def count_trusted_rows(path, date_col, start, end):
    n = 0
    for r in csv.DictReader(open(path)):
        d = date.fromisoformat(r[date_col])
        if start <= d <= end:
            n += 1
    return n


def reconcile(name, source_path, trusted_path, date_col, start, end):
    src = count_source_rows(source_path, date_col, start, end)
    tgt = count_trusted_rows(trusted_path, date_col, start, end)
    status = "MATCH" if src == tgt else "MISMATCH"
    return {"table": name, "source": src, "trusted": tgt, "diff": src - tgt, "status": status}


if __name__ == "__main__":
    start, end = date(2026, 1, 1), date(2026, 3, 31)
    res = reconcile("sell_in", "data/raw/sell_in.csv", "data/trusted/trusted_sell_in.csv",
                    "order_date", start, end)
    print(res)
    sys.exit(0 if res["status"] == "MATCH" else 1)
