-- Scenario 6.1: the Unity Catalog function the agent uses as its tool.
-- Run in the SQL Editor (Serverless Starter Warehouse). Synthetic data only.
-- The agent gets the description from the COMMENTs, so keep them accurate.
CREATE OR REPLACE FUNCTION workspace.fizzco.get_recon_status(
  feed STRING COMMENT 'Data feed to look up: sell_in, sell_out, inventory or promo',
  recon_date STRING COMMENT 'Reconciliation cut-off date in YYYY-MM-DD format, for example 2026-03-31'
)
RETURNS STRING
COMMENT 'Returns every reconciliation run (run id, job id, row counts, difference, status, note) for one feed on one cut-off date, in id order. A rerun after a failure appears as a second line. Returns a plain message when no run exists.'
RETURN (
  SELECT CASE
    WHEN COUNT(*) = 0 THEN concat('No reconciliation run found for feed ', get_recon_status.feed, ' on ', get_recon_status.recon_date)
    ELSE array_join(sort_array(collect_list(concat(
      r.recon_id, ' | job ', r.job_id, ' | feed ', r.feed, ' | date ', CAST(r.recon_date AS STRING),
      ' | source_rows ', CAST(r.source_rows AS STRING), ' | trusted_rows ', CAST(r.trusted_rows AS STRING),
      ' | diff_rows ', CAST(r.diff_rows AS STRING), ' | status ', r.status, ' | note ', COALESCE(r.note, '')))), '\n')
  END
  FROM workspace.fizzco.gold_recon_results r
  WHERE r.feed = get_recon_status.feed
    AND r.recon_date = try_cast(get_recon_status.recon_date AS DATE)
);

-- Checks (run after the CREATE). Expected results are in the comments.
SELECT workspace.fizzco.get_recon_status('sell_in', '2026-03-31');   -- two lines: RECON-0009 ... MISMATCH (63, 60, 3) and RECON-0013 ... MATCH (63, 63, 0, rerun)
SELECT workspace.fizzco.get_recon_status('sell_out', '2026-03-31');  -- one line: RECON-0010 ... MATCH, 127 and 127
SELECT workspace.fizzco.get_recon_status('promo', '2026-04-30');     -- No reconciliation run found for feed promo on 2026-04-30
SELECT workspace.fizzco.get_recon_status('sell_in', 'not a date');   -- No reconciliation run found ... (no error)
