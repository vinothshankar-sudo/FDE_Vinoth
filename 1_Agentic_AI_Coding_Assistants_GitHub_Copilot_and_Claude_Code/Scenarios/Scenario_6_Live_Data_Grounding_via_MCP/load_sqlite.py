"""Load the trusted CSVs into SQLite. AI-generated; a human reviews before commit."""
import csv
import logging
import sqlite3
import sys
from pathlib import Path

logger = logging.getLogger("load_sqlite")

BASE_DIR = Path(__file__).resolve().parent
TRUSTED_DIR = BASE_DIR / "data" / "trusted"
DB_PATH = BASE_DIR / "fizzco.db"

TEXT, INTEGER, REAL = "TEXT", "INTEGER", "REAL"
CASTS = {TEXT: str, INTEGER: int, REAL: float}

TABLES = {
    "trusted_sell_in": [
        ("order_date", TEXT), ("retailer_id", TEXT), ("sku", TEXT),
        ("units", INTEGER), ("gross_amount", REAL),
        ("discount_amount", REAL), ("net_amount", REAL),
    ],
    "trusted_inventory": [
        ("snapshot_date", TEXT), ("dc_id", TEXT), ("sku", TEXT),
        ("stock_on_hand", INTEGER),
    ],
    "trusted_promo": [
        ("promo_id", TEXT), ("sku", TEXT), ("retailer_id", TEXT),
        ("start_date", TEXT), ("end_date", TEXT),
        ("discount_pct", REAL), ("promo_days", INTEGER),
    ],
}


def read_rows(csv_path, columns):
    names = [name for name, _ in columns]
    with open(csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != names:
            raise ValueError(f"{csv_path}: header {reader.fieldnames} != expected {names}")
        rows = []
        for line_no, row in enumerate(reader, start=2):
            try:
                rows.append(tuple(CASTS[col_type](row[name]) for name, col_type in columns))
            except (ValueError, TypeError) as exc:
                raise ValueError(f"{csv_path} line {line_no}: bad row {row}: {exc}") from exc
    return rows


def load_table(conn, table, columns):
    csv_path = TRUSTED_DIR / f"{table}.csv"
    logger.info("step start: load %s from %s", table, csv_path)
    rows = read_rows(csv_path, columns)
    col_defs = ", ".join(f"{name} {col_type}" for name, col_type in columns)
    placeholders = ", ".join("?" for _ in columns)
    conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.execute(f"CREATE TABLE {table} ({col_defs})")
    conn.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)
    logger.info("step end: loaded %d rows into %s", len(rows), table)


def main():
    logger.info("step start: load trusted CSVs into %s", DB_PATH)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            for table, columns in TABLES.items():
                load_table(conn, table, columns)
            for table in TABLES:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                logger.info("row count: %s = %d", table, count)
    except (OSError, ValueError, sqlite3.Error) as exc:
        logger.error("load failed for %s: %s", DB_PATH, exc)
        return 1
    logger.info("step end: load complete")
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    sys.exit(main())
