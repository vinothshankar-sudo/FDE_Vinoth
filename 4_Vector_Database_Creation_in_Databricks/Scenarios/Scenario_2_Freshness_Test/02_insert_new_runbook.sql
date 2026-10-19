-- Scenario 4.2: freshness test. TEST ONLY row (synthetic); the cleanup statement removes it again.
-- STATEMENT
INSERT INTO workspace.fizzco.runbook_chunks (chunk_id, doc_id, title, feed, doc_type, section, position, n_tokens, text)
VALUES (
  'RB-TEST-FRESHNESS-001#c1', 'RB-TEST-FRESHNESS-001', 'Runbook: sell_out scan file arrives late (TEST ONLY)',
  'sell_out', 'runbook', 'Late scan file', 1, 70,
  'Runbook: sell_out scan file arrives late. TEST ONLY document used to time Vector Search freshness; it is not a real Fizzco procedure. The retailer scan file for sell_out should arrive by 06:30 UTC. If it has not arrived, wait until 08:00 UTC before raising an incident. After 08:00 UTC, ask the retailer owner to resend the scan file, then trigger the sell_out pipeline manually with the load_date set to the missing day.'
);
-- STATEMENT
DELETE FROM workspace.fizzco.runbook_chunks WHERE chunk_id = 'RB-TEST-FRESHNESS-001#c1';
