---
doc_id: RB-GENERAL-001
title: Runbook - first response to any pipeline failure
doc_type: runbook
feed: all
owner: Fizzco Data Engineering (fictional team)
last_reviewed: 2026-04-02
---
# Runbook: first response to any pipeline failure

## When to use this runbook
Use this runbook when a Fizzco job fails and you do not yet know which feed is affected, or when the feed-specific runbook does not explain the failure. Each feed has its own runbook for sell_in, sell_out, inventory and promo; use the feed runbook as soon as you know the feed.

## First five minutes
1. Write down the job id (format `JOB-####`), the pipeline name (format `pl_fizzco_<feed>_load`) and the load_date.
2. Find the failed activity in the pipeline monitor. Pipelines have a copy activity first and a notebook activity second. Inventory has a third activity, the archive step.
3. Check whether the load_date parameter was set. It has no default value, so a manual run without it fails at once.
4. Check whether the same failure happened on the previous day.
5. Do not edit trusted or gold tables by hand. Do not delete files from `fizzco-landing`.

## Retry and timeout behaviour
The pipelines have no automatic retry and no timeout policy. A failed run stays failed until someone reruns it. There is no failure alert either, so a failure is found by looking at the pipeline monitor or by the reconciliation. This is a known gap and is listed in the lineage documents under risks.

## Severity
| Severity | Meaning | Example |
|---|---|---|
| Sev 1 | Blocks cutover or leaves a feed without data for more than one day | Two feeds failed on the cutover day |
| Sev 2 | One feed late or a reconciliation MISMATCH that is not yet explained | JOB-0049, sell_in MISMATCH on 31 March |
| Sev 3 | A cosmetic or archive-only problem; the trusted data is correct | Archive step failed after a good transform |

## Escalation
Raise a ticket in the data-engineering queue. Include the job id, the pipeline name, the load_date, the failed activity, the severity and the reconciliation output.

## After the fix
Rerun, run the reconciliation, and write a short note in the `note` column of the reconciliation result. Close the ticket only when the reconciliation shows MATCH.
