"""Generate the CREATE TABLE statement for trusted_returns (synthetic data only)."""
import logging
import sys

LOGGER = logging.getLogger("generate_trusted_returns_ddl")

TABLE_NAME = "trusted_returns"
COLUMNS = [
    ("return_date", "DATE", "NOT NULL"),
    ("retailer_id", "STRING", "NOT NULL"),
    ("sku", "STRING", "NOT NULL"),
    ("units_returned", "INT", "NOT NULL"),
    ("reason_code", "STRING", ""),
]


def build_create_table(table_name, columns):
    if not table_name.startswith(("raw_", "trusted_")):
        raise ValueError(f"table name must start with raw_ or trusted_: {table_name!r}")
    lines = [f"    {name} {dtype} {constraint}".rstrip() for name, dtype, constraint in columns]
    return f"CREATE TABLE {table_name} (\n" + ",\n".join(lines) + "\n);"


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    LOGGER.info("start: building DDL for %s", TABLE_NAME)
    try:
        ddl = build_create_table(TABLE_NAME, COLUMNS)
    except ValueError as exc:
        LOGGER.error("failed to build DDL: %s", exc)
        return 1
    sys.stdout.write(ddl + "\n")
    LOGGER.info("end: generated DDL with %d columns", len(COLUMNS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
