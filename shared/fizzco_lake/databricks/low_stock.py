# Raw inventory: SKUs whose total stock_on_hand is below a threshold.
import csv
import logging
from collections import defaultdict
from pathlib import Path

LOW_STOCK_THRESHOLD = 1000
INVENTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "inventory.csv"

logger = logging.getLogger(__name__)


def get_low_stock_skus(path=INVENTORY_PATH, threshold=LOW_STOCK_THRESHOLD):
    """Return a sorted list of SKUs whose summed stock_on_hand is below threshold."""
    logger.info("start get_low_stock_skus path=%s threshold=%s", path, threshold)
    totals = defaultdict(int)
    row_count = 0
    try:
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                row_count += 1
                try:
                    totals[row["sku"]] += int(row["stock_on_hand"])
                except (KeyError, ValueError) as exc:
                    raise ValueError(f"bad row {row_count} in {path}: {row!r}") from exc
    except FileNotFoundError:
        logger.error("inventory file not found: %s", path)
        raise
    result = sorted(sku for sku, total in totals.items() if total < threshold)
    logger.info("read %d rows, %d skus, %d below %s", row_count, len(totals), len(result), threshold)
    logger.info("end get_low_stock_skus")
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    logger.info("low stock skus: %s", get_low_stock_skus())
