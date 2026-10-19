# Module 6: Databricks Agent Creation

An agent is a language model that can choose and call tools (a function, a search, a Genie space) to answer a question. This module builds one for the Fizzco story, tests it, and deploys it.

## Scenarios

| # | Scenario | Status |
|---|---|---|
| 1 | [First tool-calling agent](#scenario-1-first-tool-calling-agent) | Done |
| 2 | [Multi-tool composition](#scenario-2-multi-tool-composition) | Done (the "needs both tools" answer is incomplete) |
| 3 | [Evaluation before trust](#scenario-3-evaluation-before-trust) | Done (5 of 12 questions failed) |
| 4 | [Tracing and root cause](#scenario-4-tracing-and-root-cause) | Done |
| 5 | [Deployment and monitoring](#scenario-5-deployment-and-monitoring) | Done (Genie tool fails on the endpoint) |

The shared agent code is in the `agent/` folder (`fizzco_agent.py` is the agent, `fizzco_serving_agent.py` wraps it for deployment, `fizzco_eval.py` holds the test checks, and the `test_*.py` files are offline tests). To run the notebooks, put the agent files and the notebooks in one Databricks workspace folder (I used `fizzco-agent`) and run them on Serverless compute. No credentials are stored in any file.

## Scenario 1: First tool-calling agent

Folder: `Scenarios/Scenario_1_First_Tool_Calling_Agent/` (files and `evidence/` screenshots are inside).

### Task

Register one Unity Catalog function as a tool. Build an agent that knows when to call it and when to just answer.

### What I did

- Made a function, `get_recon_status(feed, recon_date)`, that returns the reconciliation runs for one feed on one date (`01_create_get_recon_status.sql`).
- Gave it to an agent as its only tool (`nb_6_1_first_agent.py`, agent code in `agent/fizzco_agent.py`).
- Asked four questions: two about Fizzco data, a greeting, and 12 times 12.

### Result

| Question | Used the tool? | Right? |
|---|---|---|
| sell_in on 31 March 2026 | Yes | Yes |
| promo on 28 February 2026 | Yes | Yes |
| Hello! What can you help me with? | No | Yes |
| What is 12 times 12? | No | Yes |

For the sell_in question the answer named both runs: RECON-0009 (mismatch) and the rerun RECON-0013 (match). I checked this against the data.

Screenshots are in `evidence/`: the table of four questions and the trace of the sell_in call.

### Limits

- Four questions, one run each. This shows it works, not how often.
- I did not capture a direct call of the function, and the DESCRIBE screenshot shows only config rows.

### Lesson

The model picks a tool from its description, so the description matters. Check the arguments in the trace, not only the final answer.

## Scenario 2: Multi-tool composition

Folder: `Scenarios/Scenario_2_Multi_Tool_Composition/` (files and `evidence/` screenshots are inside).

### Task

Add a second tool to the agent. Test questions that need each tool alone, and one that needs both.

### What I did

The agent now has three tools (`nb_6_2_multi_tool.py`):

| Tool | Used for |
|---|---|
| get_recon_status | Reconciliation runs |
| search_runbooks | Runbook and incident notes (vector search) |
| ask_genie | Business numbers (Genie space "Retail Sales & Promotions Analytics") |

### Result

- Each single-tool question used the right tool. Genie gave West 12,463.04 and East 9,893.50.
- The question that needs both tools was: "Why did sell_in fail on 31 March and what do I do?"

| Run | What happened |
|---|---|
| 1 | Used only the runbook tool |
| 2 | Used only the status tool and quoted a source it had not looked up |
| 3 | Used both tools, but the answer left out the first failed run (RECON-0009) |

I tightened the prompt rules after runs 1 and 2. Run 3 is the best I got. It is still not a complete answer.

Screenshots are in `evidence/` (Genie spaces, the four-question table, traces, and the first two hero runs).

### Limits

- The hero answer is incomplete.
- One run per question. Changing the prompt fixed one problem and caused another, so results can change.

### Lesson

A second tool means the model also has to choose between tools, and it does not always pick both. Test the "needs both" case on its own.

## Scenario 3: Evaluation before trust

Folder: `Scenarios/Scenario_3_Evaluation_Before_Trust/` (files and `evidence/` screenshots are inside).

### Task

Make a small test set of 10 to 15 questions with expected answers, run the agent on it, and write down at least one failure.

### What I did

- Wrote 12 questions with expected facts and expected tools (`eval_set.csv`): easy ones, one that needs two tools, edge cases, and plain chat.
- Ran the agent on all 12 (`nb_6_3_evaluation.py`) with three checks: do the expected facts appear, were the right tools used, and an AI judge for correctness.

### Result

| Check | Score |
|---|---|
| Expected facts present | 0.667 |
| Right tools used | 0.917 |
| AI judge: correct | 0.917 |

5 of 12 questions failed at least one check:

| Question | Problem |
|---|---|
| E1, E2 | Answer did not give the row counts |
| E6 | The Genie tool timed out |
| M1 | Left out the failed run |
| X3 | Answered a policy question without searching the runbooks |

I did not change the questions or checks after seeing the results. Screenshots are in `evidence/`.

### Limits

12 questions is a small sample, and each was run once.

### Lesson

An agent can look fine in a few manual tries and still fail on one in three questions. Write the test set first and run it.

## Scenario 4: Tracing and root cause

Folder: `Scenarios/Scenario_4_Tracing_and_Root_Cause/` (files and `evidence/` screenshots are inside).

### Task

Break one tool on purpose. Use the trace to find which step caused the wrong answer, without re-reading the agent code.

### What I did (`nb_6_4_tracing_root_cause.py`)

1. Asked "What was the reconciliation status of sell_in on 31 March 2026?" and got the right answer.
2. Pointed the function at a stale copy of the table (rows before 31 March only).
3. Asked the same question again.
4. Opened the trace, found the problem, then put the function back.

### Result

| Run | Answer |
|---|---|
| Before | MISMATCH first, then a rerun that matched |
| Broken | "No reconciliation run found" |
| Restored | Right answer again |

In the broken run every step in the trace showed OK, so nothing looked wrong. The question and the tool arguments were the same in all three runs. That ruled out the model and the prompt, so the problem had to be the tool and its data. Restoring the function fixed it.

Screenshots are in `evidence/` (before, broken and restored).

### Limits

- I did not capture the tool step's own output, so "the tool returned nothing" is concluded from the answer and the trace, not seen directly.
- The first call took about 6 minutes. Later calls took about 2 seconds.

### Lesson

A wrong answer can come with no error at all. Comparing the traces of a good and a bad run is the fastest way to find the step.

## Scenario 5: Deployment and monitoring

Folder: `Scenarios/Scenario_5_Deployment_and_Monitoring/` (files and `evidence/` screenshots are inside).

### Task

Deploy the agent to a Model Serving endpoint, send a few live requests, and show how I would monitor it.

### What I did (`nb_6_5_deploy_monitor.py`)

- Packaged the agent, registered it in Unity Catalog (`workspace.fizzco.fizzco_agent`, version 1) and deployed it.
- The endpoint was ready after about 9 minutes.
- Sent six requests to it.

### Result

| Request | Worked? | Time |
|---|---|---|
| Recon status | Yes | 42.7 s (first call after idle) |
| Runbook question | Yes | 3.8 s |
| Business numbers (Genie) | No, the Genie tool failed | 5.0 s |
| Why did sell_in fail? (needs both tools) | Yes | 7.3 s |
| Hello | Yes | 1.2 s |
| Empty request | Rejected on purpose | 0.1 s |

5 of 6 behaved as expected. Genie works in the notebook but fails on the endpoint. I did not find the exact cause. My best guess is the endpoint was not given access to the tables behind the Genie space. I did not fix it because this scenario does not need Genie.

### How I would monitor it

- Traces list: every request with its question, answer, time and OK or Error (`evidence/17`).
- Metrics tab: error rate, CPU, memory (`evidence/16`).
- The endpoint has no inference table, so there is no p50 or p95.

Screenshots are in `evidence/` (setup, deploy, ready, live requests, endpoint page, metrics, traces).

### Limits

- The Genie problem above.
- Only six requests, no load test.
- The first request after idle is slow (42.7 s).

### Lesson

An endpoint can look healthy while one tool inside it fails. The trace is where it shows.

## AI use

I used an AI assistant to help build and write this module. I ran everything in Databricks myself, took the screenshots and checked the results. All data is synthetic.
