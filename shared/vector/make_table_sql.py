"""Generate the Scenario 4.1 table script from the 200-word / 40-overlap chunks chosen in Scenario 3.2.

Run:  python3 shared/vector/make_table_sql.py
Writes 4_Vector_Database_Creation_in_Databricks/Scenarios/Scenario_1_End_to_End_Index_Build/01_create_runbook_chunks.sql
Pure local step: no credentials, no Databricks calls.
"""
import sys

import vs_lib as V

OUT = (V.ASSIGNMENT_DIR / "4_Vector_Database_Creation_in_Databricks" / "Scenarios"
       / "Scenario_1_End_to_End_Index_Build" / "01_create_runbook_chunks.sql")

DDL = f"""-- Scenario 4.1: source Delta table for the Vector Search index (synthetic Fizzco runbook chunks).
-- Change Data Feed is switched on because a Delta Sync index reads the table's change feed.
-- STATEMENT
CREATE TABLE IF NOT EXISTS {V.TABLE} (
  chunk_id   STRING NOT NULL COMMENT 'Primary key: <doc_id>#c<position>',
  doc_id     STRING COMMENT 'Source document id',
  title      STRING COMMENT 'Source document title',
  feed       STRING COMMENT 'Metadata for filtering: sell_in, sell_out, inventory, promo, all',
  doc_type   STRING COMMENT 'Metadata for filtering: runbook, policy, glossary, handbook, ...',
  section    STRING COMMENT 'Nearest heading above the chunk',
  position   INT    COMMENT 'Chunk number inside its document',
  n_tokens   INT    COMMENT 'Words in the chunk (word count is the token proxy)',
  text       STRING COMMENT 'Chunk text that is embedded'
)
COMMENT 'Fizzco runbook and policy chunks, 200 words with 40 overlap (Scenario 3.2 setting). Synthetic data.'
TBLPROPERTIES (delta.enableChangeDataFeed = true);
"""


def main() -> int:
    chunks = V.build_chunks()
    values = ",\n".join("  " + V.chunk_row_sql(c) for c in chunks)
    text = (DDL + "-- STATEMENT\n-- Run only when the table is empty (the run script checks this first).\n"
            f"INSERT INTO {V.TABLE} (chunk_id, doc_id, title, feed, doc_type, section, position, n_tokens, text) VALUES\n"
            + values + ";\n")
    OUT.write_text(text, encoding="utf-8")
    feeds = {}
    for c in chunks:
        feeds[c.feed] = feeds.get(c.feed, 0) + 1
    V.out(f"Wrote {OUT.name}: {len(chunks)} rows. Rows per feed: {dict(sorted(feeds.items()))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
