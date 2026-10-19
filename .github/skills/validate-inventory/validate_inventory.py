"""Validate an application object inventory CSV against the template (synthetic data only).

Usage: python3 validate_inventory.py <inventory.csv>
Exit codes: 0 PASS, 1 FAIL, 2 file cannot be read.
"""
import csv
import logging
import sys
from pathlib import Path

LOGGER = logging.getLogger("validate_inventory")
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s - %(message)s"

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_PATH = REPO_ROOT / "shared" / "inventory" / "App_Object_Inventory_Template.csv"

VALID_OBJECT_TYPES = {"Pipeline", "Notebook", "Table"}
VALID_STATUSES = {"Active", "Retired"}

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_UNREADABLE = 2


def read_template_columns(path):
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            header = next(csv.reader(f), None)
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        raise ValueError(f"cannot read template {path}: {exc}") from exc
    if not header:
        raise ValueError(f"template {path} is empty")
    return [c.strip() for c in header]


def read_inventory(path):
    """Return (header, rows) where rows are (file_line_number, dict); header is line 1."""
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header is None:
                raise ValueError(f"inventory {path} is empty")
            header = [c.strip() for c in header]
            rows = []
            for values in reader:
                if not any(v.strip() for v in values):
                    continue
                row = {col: (values[i].strip() if i < len(values) else "")
                       for i, col in enumerate(header)}
                rows.append((reader.line_num, row))
    except (OSError, csv.Error, UnicodeDecodeError) as exc:
        raise ValueError(f"cannot read inventory {path}: {exc}") from exc
    return header, rows


def check_columns(header, expected):
    if header == expected:
        return []
    return [(1, "", "R1", f"columns {header} do not match template {expected} (names and order)")]


def check_rows(rows):
    violations = []
    first_line_of_id = {}
    known_ids = {row.get("object_id", "") for _, row in rows}
    for line, row in rows:
        oid = row.get("object_id", "")
        if oid in first_line_of_id:
            violations.append((line, oid, "R2",
                               f"duplicate object_id (first seen on line {first_line_of_id[oid]})"))
        else:
            first_line_of_id[oid] = line
        dep = row.get("depends_on", "")
        if dep and dep not in known_ids:
            violations.append((line, oid, "R3", f"depends_on '{dep}' not found as an object_id"))
        otype = row.get("object_type")
        if otype is not None and otype not in VALID_OBJECT_TYPES:
            violations.append((line, oid, "R4",
                               f"object_type '{otype}' not in {sorted(VALID_OBJECT_TYPES)}"))
        status = row.get("status")
        if status is not None and status not in VALID_STATUSES:
            violations.append((line, oid, "R5",
                               f"status '{status}' not in {sorted(VALID_STATUSES)}"))
    return violations


def format_report(violations):
    lines = ["| line | object_id | rule | detail |", "|---|---|---|---|"]
    for line, oid, rule, detail in sorted(violations, key=lambda v: (v[0], v[2])):
        lines.append(f"| {line} | {oid} | {rule} | {detail.replace('|', '/')} |")
    lines.append("FAIL" if violations else "PASS")
    return "\n".join(lines)


def main(argv):
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, stream=sys.stderr)
    if len(argv) != 2:
        LOGGER.error("usage: validate_inventory.py <inventory.csv>; got arguments %s", argv[1:])
        return EXIT_UNREADABLE
    inventory_path = argv[1]
    LOGGER.info("step start: validate %s against template %s", inventory_path, TEMPLATE_PATH)
    try:
        expected = read_template_columns(TEMPLATE_PATH)
        header, rows = read_inventory(inventory_path)
    except ValueError as exc:
        LOGGER.error("%s", exc)
        return EXIT_UNREADABLE
    LOGGER.info("row count: %d data rows read from %s", len(rows), inventory_path)

    violations = check_columns(header, expected) + check_rows(rows)
    sys.stdout.write(format_report(violations) + "\n")
    LOGGER.info("step end: %d violation(s)", len(violations))
    return EXIT_FAIL if violations else EXIT_PASS


if __name__ == "__main__":
    sys.exit(main(sys.argv))
