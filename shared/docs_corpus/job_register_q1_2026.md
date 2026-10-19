---
doc_id: REG-Q1-2026-001
title: Job and reconciliation register - Q1 2026
doc_type: register
feed: all
owner: Fizzco Data Engineering (fictional team)
last_reviewed: 2026-04-02
---
# Job and reconciliation register: Q1 2026

## How to read this register
Each line is one reconciliation run. A reconciliation run is executed by a job (format `JOB-####`) and produces a result (format `RECON-####`). Row counts are cumulative from 1 January 2026 up to and including the cut-off date. Status is MATCH when diff_rows is 0 and MISMATCH otherwise. There were 13 runs in the quarter, 12 MATCH and 1 MISMATCH. The one MISMATCH was RECON-0009 (job JOB-0049, sell_in, 31 March 2026); its rerun RECON-0013 (job JOB-0053) was MATCH.

## Register by cut-off date

### January month end (2026-01-31)

- RECON-0001 is job JOB-0041, feed sell_in, cut-off 2026-01-31: source 24 rows, trusted 24 rows, difference 0, status MATCH.
- RECON-0002 is job JOB-0042, feed sell_out, cut-off 2026-01-31: source 48 rows, trusted 48 rows, difference 0, status MATCH.
- RECON-0003 is job JOB-0043, feed inventory, cut-off 2026-01-31: source 10 rows, trusted 10 rows, difference 0, status MATCH.
- RECON-0004 is job JOB-0044, feed promo, cut-off 2026-01-31: source 8 rows, trusted 8 rows, difference 0, status MATCH.

### February month end (2026-02-28)

- RECON-0005 is job JOB-0045, feed sell_in, cut-off 2026-02-28: source 38 rows, trusted 38 rows, difference 0, status MATCH.
- RECON-0006 is job JOB-0046, feed sell_out, cut-off 2026-02-28: source 78 rows, trusted 78 rows, difference 0, status MATCH.
- RECON-0007 is job JOB-0047, feed inventory, cut-off 2026-02-28: source 29 rows, trusted 29 rows, difference 0, status MATCH.
- RECON-0008 is job JOB-0048, feed promo, cut-off 2026-02-28: source 12 rows, trusted 12 rows, difference 0, status MATCH.

### March quarter end (2026-03-31)

- RECON-0009 is job JOB-0049, feed sell_in, cut-off 2026-03-31: source 63 rows, trusted 60 rows, difference 3, status MISMATCH. Note: date filter excluded the end date; 3 rows dated 2026-03-31 not counted.
- RECON-0010 is job JOB-0050, feed sell_out, cut-off 2026-03-31: source 127 rows, trusted 127 rows, difference 0, status MATCH.
- RECON-0011 is job JOB-0051, feed inventory, cut-off 2026-03-31: source 40 rows, trusted 40 rows, difference 0, status MATCH.
- RECON-0012 is job JOB-0052, feed promo, cut-off 2026-03-31: source 12 rows, trusted 12 rows, difference 0, status MATCH.
- RECON-0013 is job JOB-0053, feed sell_in, cut-off 2026-03-31: source 63 rows, trusted 63 rows, difference 0, status MATCH. Note: rerun after the end-date fix.

## Quick facts
- The first job of the quarter is JOB-0041 and the last is JOB-0053.
- Each month end has one reconciliation per feed: sell_in, sell_out, inventory and promo, run in that order.
- The only rerun in Q1 2026 is JOB-0053 (RECON-0013), which re-reconciled sell_in for 2026-03-31 after the end-date fix.
