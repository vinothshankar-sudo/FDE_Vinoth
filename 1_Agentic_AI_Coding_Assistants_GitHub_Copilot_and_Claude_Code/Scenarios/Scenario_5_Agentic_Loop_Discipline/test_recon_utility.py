import csv
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "databricks"))
import recon_utility as ru

START, END = date(2026, 1, 1), date(2026, 3, 31)
ROWS = [("2026-01-01", "a"), ("2026-02-15", "b"), ("2026-03-31", "c"), ("2026-04-01", "d")]


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["order_date", "sku"])
        w.writerows(rows)


class TestReconUtility(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raw = os.path.join(self.tmp.name, "raw.csv")
        self.trusted = os.path.join(self.tmp.name, "trusted.csv")

    def test_identical_files_match_including_end_date(self):
        write_csv(self.raw, ROWS)
        write_csv(self.trusted, ROWS)
        res = ru.reconcile("t", self.raw, self.trusted, "order_date", START, END)
        self.assertEqual(res["status"], "MATCH")
        self.assertEqual(res["diff"], 0)
        self.assertEqual(res["source"], 3)

    def test_both_counters_include_start_and_end_dates(self):
        write_csv(self.raw, ROWS)
        self.assertEqual(ru.count_source_rows(self.raw, "order_date", START, END), 3)
        self.assertEqual(ru.count_trusted_rows(self.raw, "order_date", START, END), 3)

    def test_missing_row_still_mismatches(self):
        write_csv(self.raw, ROWS)
        write_csv(self.trusted, ROWS[:2] + ROWS[3:])
        res = ru.reconcile("t", self.raw, self.trusted, "order_date", START, END)
        self.assertEqual(res["status"], "MISMATCH")
        self.assertEqual(res["diff"], 1)

    def test_real_sell_in_files_match(self):
        base = os.path.join(os.path.dirname(__file__), "..", "data")
        res = ru.reconcile("sell_in", os.path.join(base, "raw", "sell_in.csv"),
                           os.path.join(base, "trusted", "trusted_sell_in.csv"),
                           "order_date", START, END)
        self.assertEqual(res["status"], "MATCH")
        self.assertEqual(res["source"], 63)
        self.assertEqual(res["trusted"], 63)


if __name__ == "__main__":
    unittest.main()
