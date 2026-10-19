"""Recon status tab: queries gold_recon_results on a SQL warehouse (synthetic data only)."""
import logging
import os

import streamlit as st
from databricks import sql
from databricks.sdk.core import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
LOGGER = logging.getLogger("recon_status_app")

QUERY = (
    "SELECT recon_id, job_id, feed, recon_date, source_rows, trusted_rows, diff_rows, status "
    "FROM workspace.fizzco.gold_recon_results ORDER BY recon_date DESC"
)


def load_recon_status():
    warehouse_id = os.environ.get("DATABRICKS_WAREHOUSE_ID")
    if not warehouse_id:
        raise RuntimeError("DATABRICKS_WAREHOUSE_ID is not set; check the sql-warehouse resource in app.yaml")
    cfg = Config()  # credentials come from the app's service principal, injected by the platform
    LOGGER.info("start: querying warehouse %s", warehouse_id)
    with sql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/{warehouse_id}",
        credentials_provider=lambda: cfg.authenticate,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(QUERY)
            df = cur.fetchall_arrow().to_pandas()
    LOGGER.info("end: fetched %d rows", len(df))
    return df


st.title("Fizzco Migration Assurance Hub: Recon status")
try:
    st.dataframe(load_recon_status())
except (sql.Error, RuntimeError, ValueError) as exc:
    LOGGER.error("query failed for %s: %s", QUERY, exc)
    st.error(f"Could not load recon status: {exc}")
