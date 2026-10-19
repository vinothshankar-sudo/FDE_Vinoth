# Data Engineer → Forward Deployed Engineer (FDE)
## AI-Native Skills Guide: Concepts, Implementation & Assignments

**Prepared for:** Parag Shah
**Prepared by:** Sai Prashanth
**Date:** August 24, 2026

---

## Table of Contents

1. [Agentic AI Coding Assistants — GitHub Copilot & Claude Code](#1-agentic-ai-coding-assistants--github-copilot--claude-code)
2. [Databricks Genie — Conversational Analytics](#2-databricks-genie--conversational-analytics)
3. [Retrieval-Augmented Generation (RAG)](#3-retrieval-augmented-generation-rag)
4. [Vector Database Creation in Databricks](#4-vector-database-creation-in-databricks)
5. [Databricks Apps](#5-databricks-apps)
6. [Databricks Agent Creation (Mosaic AI Agent Framework)](#6-databricks-agent-creation-mosaic-ai-agent-framework)

---

## 1. Agentic AI Coding Assistants — GitHub Copilot & Claude Code

### What It Is
Both GitHub Copilot (agent mode) and Claude Code are **agentic coding assistants** — they don't just autocomplete a line, they can read a codebase, plan a multi-step change, call tools (terminal, file edits, search), verify the result, and iterate until the task is actually done. Getting fast, reliable output depends on understanding their building blocks, not just typing prompts.

### Key Concepts & How to Implement Them

| Concept | What It Is | How to Implement |
|---|---|---|
| **Agentic loop** | The repeating cycle: perceive (read code/errors) → plan → act (tool call) → verify (tests/lint) → repeat until done | Structure every non-trivial ask as: describe the goal + constraints, let the agent build a plan/todo list, and explicitly ask it to verify (run tests, check errors) before declaring done |
| **Agents / custom agent modes** | A specialized persona with a defined scope and restricted tool access (e.g., a "reviewer" agent that only reads, never edits) | Copilot: create a `*.agent.md` file with a system prompt + tool allowlist. Claude Code: define a project-level agent config the same way — narrow scope = more reliable output |
| **Sub-agents** | A delegated, often stateless agent spawned to do one bounded job (investigate, build one file, review a diff) and return a compressed result — keeps the main conversation's context window clean | Use `runSubagent` (Copilot) or Task-tool subagents (Claude Code) for: codebase investigation before a big change, isolated single-file edits, or an independent review pass on a diff |
| **Slash commands / prompt files** | A reusable, parameterized instruction saved once and invoked by name instead of retyped every time | Create a `.prompt.md` (Copilot) or `.claude/commands/*.md` (Claude Code) file for repeatable workflows — e.g., `/create-pr`, `/review-notebook`, `/generate-sttm` |
| **Skills** | Packaged domain knowledge (a `SKILL.md` + optional reference scripts) that the assistant auto-loads when a task matches its description | Write a `SKILL.md` describing "when to use this" + step-by-step instructions + any helper scripts — this is how the 40+ skills in this repo (notebook-creation, code-review, monitoring, etc.) work |
| **Custom instructions / project memory** | Persistent, repo-scoped conventions so every suggestion follows team standards automatically, without repeating them each session | Copilot: `.github/copilot-instructions.md` or `*.instructions.md` with `applyTo` glob scoping. Claude Code: a `CLAUDE.md` file at the project root |
| **Hooks** | Shell commands that fire automatically on lifecycle events (before/after a tool call, session start) to enforce checks the model might otherwise forget | Wire a hook to run lint/tests automatically after every file edit, so quality gates aren't dependent on the model remembering to run them |
| **MCP (Model Context Protocol)** | A standard that connects the assistant to live external systems (databases, ticketing, git) as first-class callable tools instead of the model guessing | Attach an MCP server (e.g., Databricks MCP for live SQL, GitKraken MCP for git/PR operations) so the assistant queries real systems instead of hallucinating schema/state |

### Assignments

1. **Scenario — Repeatable workflow:** Pick a task you do manually every week (e.g., generating a code review checklist, or scaffolding a new notebook). Build a slash command/prompt file for it and run it twice on two different inputs to prove it's reusable.
2. **Scenario — Context management with subagents:** Take a task that requires exploring an unfamiliar part of the codebase before making a change (e.g., "find every place a given config value is used and update it"). Delegate the investigation to a subagent, and only bring the final file list back into your main session.
3. **Scenario — Packaging a skill:** Take a process you've explained to a teammate more than once (e.g., how to validate an STTM file) and turn it into a `SKILL.md` with clear trigger conditions and step-by-step instructions. Test that the assistant picks it up automatically when you describe the task in natural language, without naming the skill.
4. **Scenario — Enforcing standards automatically:** Write a custom instructions file (`*.instructions.md` or `CLAUDE.md`) that encodes 3 real team coding conventions (naming, error handling, logging pattern). Verify the assistant follows all 3 without being reminded, across two unrelated code-generation requests.
5. **Scenario — Agentic loop discipline:** Give the assistant a bug report with no other context. Require it to (a) reproduce/diagnose using tools before editing anything, (b) propose a fix, (c) apply the fix, and (d) verify with a test or `get_errors` — reject any output that skips the verify step.
6. **Scenario — Live data grounding via MCP:** Ask a question that requires real, current data (e.g., "what's the schema of table X in our workspace") and confirm the assistant uses the connected MCP server to answer instead of guessing from training data.

---

## 2. Databricks Genie — Conversational Analytics

### What It Is
**Genie** is Databricks' AI/BI feature that lets business users ask natural-language questions against governed Unity Catalog tables and get back SQL-backed answers — no analyst required. It runs inside a **Genie Space**: a curated, scoped set of tables, metadata, and example instructions that teach Genie the business logic.

### Key Concepts & How to Implement

1. **Genie Space creation** — select the specific tables/views relevant to the use case (don't expose the entire catalog); over-scoping is the #1 cause of wrong answers.
2. **Metadata quality** — write clear table and column descriptions in Unity Catalog; Genie's answer accuracy is directly proportional to how well the schema is documented.
3. **Sample instructions / trusted queries** — add example questions with the *correct* SQL so Genie learns business-specific definitions (e.g., how "active customer" or "on-time delivery" is calculated) rather than inventing its own logic.
4. **Governance inheritance** — Genie respects Unity Catalog row/column-level security; a user only sees what their identity is already permitted to see.
5. **Genie API** — Genie conversations (start conversation, ask follow-up, retrieve generated SQL + result set) can be called programmatically, which lets Genie be embedded inside a custom app or used as a tool inside an agent.
6. **Diagnosing wrong answers** — when Genie gives an incorrect answer, the fix is almost always in the *space* (ambiguous column names, missing join relationships, no instruction covering that business term) — not re-phrasing the question repeatedly.

### Assignments

1. **Scenario — Build from scratch:** Create a Genie Space over a real Gold table set for one business domain (e.g., order fulfillment). Add table/column descriptions and at least 3 sample instructions covering common business terms.
2. **Scenario — Break and fix:** Deliberately ask Genie an ambiguous question likely to produce a wrong answer (e.g., a metric with two possible definitions). Diagnose the root cause and fix it by improving metadata/instructions — not by rewording the question.
3. **Scenario — Governance check:** Test the same Genie Space with two different user identities that have different Unity Catalog row-level permissions, and confirm Genie's answers correctly differ based on access.
4. **Scenario — Programmatic access:** Use the Genie API to start a conversation, ask a follow-up question in the same thread, and extract the generated SQL — without touching the UI.
5. **Scenario — Business handoff:** Take a stakeholder's vague ask ("show me how markets are performing") and turn it into a working Genie Space demo in under an hour, documenting what scope decisions you made and why.

---

## 3. Retrieval-Augmented Generation (RAG)

### What It Is
RAG grounds an LLM's answer in real, current information by retrieving relevant content from an external source at query time, instead of relying only on what the model memorized during training. This is the pattern behind document Q&A bots, internal knowledge assistants, and any "chat with our data/docs" ask.

### Key Concepts & How to Implement

The standard pipeline:

```
Source documents → Chunking → Embedding → Vector Index → Retriever
        → (query + retrieved context) → LLM → Grounded, cited answer
```

1. **Chunking** — split source documents (PDFs, Confluence pages, STTMs) into semantically coherent pieces. Chunk size/overlap is a real design decision: too small loses context, too large dilutes retrieval precision.
2. **Embedding** — convert each chunk into a vector using an embedding model (e.g., a Databricks Foundation Model API embedding endpoint).
3. **Indexing** — load embeddings into a vector store for similarity search (see Section 4).
4. **Retrieval** — at query time, embed the user's question and pull the top-k most relevant chunks, optionally filtered by metadata (document type, date, sector) and re-ranked.
5. **Augmented generation** — inject the retrieved chunks into the LLM prompt as grounding context, and require the answer to cite its sources.
6. **Evaluation** — measure retrieval quality (did it fetch the right chunks?) and answer groundedness (is the answer actually supported by the retrieved context?) — don't just eyeball a few examples.

### Assignments

1. **Scenario — Baseline pipeline:** Build a RAG pipeline over a small internal document set (e.g., a handful of STTM/DRD documents): chunk, embed, index, retrieve, and answer 5 test questions with citations back to the source chunk.
2. **Scenario — Chunking tradeoffs:** Run the same document set through two different chunking strategies (e.g., 200 vs. 800 tokens, with/without overlap) and compare retrieval quality on the same 5 test questions. Document which strategy worked better and why.
3. **Scenario — Metadata-filtered retrieval:** Add a metadata field (e.g., document type or sector) to your chunks, and build a query that filters retrieval to only the relevant subset before answering.
4. **Scenario — Groundedness failure hunt:** Deliberately ask a question the source documents do *not* answer, and confirm the system says so rather than hallucinating an answer. Fix the prompt/pipeline if it doesn't.
5. **Scenario — Hybrid retrieval:** Combine keyword search with semantic (vector) search for one query where pure semantic search underperforms (e.g., an exact code/ID lookup), and show the improvement.

---

## 4. Vector Database Creation in Databricks

### What It Is
**Databricks Vector Search** is the managed vector database layer that powers RAG and semantic search directly on governed Delta/Unity Catalog data — no separate vector database infrastructure to stand up or maintain.

### Key Concepts & How to Implement

| Concept | Detail |
|---|---|
| **Vector Search Endpoint** | The compute layer that serves vector queries — must be created before any index can be built on top of it |
| **Delta Sync Index** | An index that automatically stays in sync with a source Delta table (requires Change Data Feed enabled) — new/changed rows are re-embedded and re-indexed without manual intervention; the default choice for governed, evolving data |
| **Direct Vector Access Index** | An index where embeddings are pushed/managed directly via API — used when embeddings are computed outside Databricks or when you need finer control over what's indexed and when |
| **Embedding source** | Either a pre-computed embedding vector column in Delta, or a text column that Databricks embeds automatically using a specified embedding model endpoint |
| **Similarity search** | Queried via the `vector_search()` SQL function or the Vector Search Python SDK, with `top_k` and optional metadata filters |

**Build sequence:**
1. Land source content into a Delta table with a text column, with CDF enabled.
2. Create (or reuse) a Vector Search endpoint.
3. Create a Delta Sync Index on the table, specifying the embedding model.
4. Query the index via SQL or the SDK with top-k + filters.
5. Wire the retriever into a RAG chain (Section 3) or expose it as a tool to an agent (Section 6).

### Assignments

1. **Scenario — End-to-end index build:** Starting from a Delta table with CDF enabled, create a Vector Search endpoint and a Delta Sync Index, and run a basic `similarity_search` query against it.
2. **Scenario — Freshness test:** Insert a new row into the source Delta table after the index is built, and verify (and time) how long it takes for that row to become retrievable through the index — document the sync behavior.
3. **Scenario — Filtered search:** Add a metadata column (e.g., market or document category) to the source table and run a `similarity_search` query that combines vector similarity with a metadata filter.
4. **Scenario — Index type comparison:** Build one Delta Sync Index and one Direct Vector Access Index over the same conceptual dataset, and document the tradeoffs you observed (setup effort, update behavior, control).
5. **Scenario — Query tuning:** Compare results for the same query at `top_k=3` vs. `top_k=15`, and describe how you'd choose `top_k` for a real RAG use case based on what you saw.

---

## 5. Databricks Apps

### What It Is
**Databricks Apps** let you build and host interactive applications (Streamlit, Gradio, Dash, or Flask) directly inside the Databricks workspace, with native, governed access to Unity Catalog data, secrets, and model-serving endpoints — no separate hosting infrastructure required.

### Key Concepts & How to Implement

1. **App structure** — an `app.yaml` (resource/compute configuration), application source code, and a requirements file, deployed via the Databricks CLI or workspace UI.
2. **Governed identity** — apps run under a service principal/OAuth identity with scoped Unity Catalog permissions; there should never be hardcoded credentials in app code.
3. **Resource wiring** — attach a SQL warehouse, a model-serving endpoint (e.g., a deployed RAG or agent endpoint), or secrets to the app at deploy time.
4. **Fit for purpose** — Apps are best for the "give the business a simple UI" ask: a front-end over a Genie conversation, a RAG chatbot, or an agent, shipped on the same platform where the data already lives.

### Assignments

1. **Scenario — Minimal deployable app:** Deploy a basic Databricks App (Streamlit or Gradio) that runs a simple query against a SQL warehouse and displays the result — no hardcoded credentials.
2. **Scenario — Front-end for Genie/RAG:** Build a small app UI that lets a user type a question and displays the answer from either a Genie conversation (Section 2) or a RAG pipeline (Section 3).
3. **Scenario — Model-serving integration:** Wire the app to call a deployed model-serving endpoint and display the response, handling a failure/timeout case gracefully in the UI.
4. **Scenario — Access control test:** Deploy the same app for two users with different Unity Catalog permissions and confirm the data shown correctly differs based on their access — not the app's own logic.
5. **Scenario — Live iteration:** Starting from a working app, make three incremental UI/feature changes (e.g., add a filter, add a chart, add an export button) one at a time, redeploying and validating after each change.

---

## 6. Databricks Agent Creation (Mosaic AI Agent Framework)

### What It Is
The **Mosaic AI Agent Framework** is Databricks' toolkit for building, evaluating, and deploying tool-calling LLM agents — the layer above a single RAG chain, where the LLM decides *which* tool to call (a SQL query, a vector search retriever, a Genie conversation, a Python function) to answer a request, potentially across multiple tools in one interaction.

### Key Concepts & How to Implement

| Concept | Detail |
|---|---|
| **Tools** | Discrete, callable capabilities exposed to the agent — most commonly **Unity Catalog Functions** (governed, reusable SQL/Python functions registered in UC), so tool access is itself access-controlled |
| **Tool-calling agent** | An LLM wrapped in an agent executor loop that decides which registered tool(s) to invoke, then synthesizes a final answer from the results |
| **Multi-tool composition** | Combining several tools in one agent — e.g., a Genie tool for structured data + a vector search retriever for unstructured docs + a UC Function for a calculation — so one agent handles both "what's our Q3 revenue" and "what's our return policy" |
| **Authoring** | Typically built with the Agent Framework plus LangChain/LangGraph or the Databricks `ResponsesAgent`/`ChatAgent` interface, with MLflow tracing for every step |
| **Agent evaluation** | **Mosaic AI Agent Evaluation** — systematically scoring agent responses for correctness, groundedness, and safety against a curated eval set using LLM-judges, before the agent is trusted for real use |
| **Deployment** | Registering the agent in Unity Catalog and deploying it as a Model Serving endpoint, with the same monitoring/governance as any served model |

**Build sequence:**
1. Register one or more Unity Catalog Functions as tools.
2. Build a tool-calling agent that can select and invoke them.
3. Add MLflow tracing so every intermediate tool call is inspectable.
4. Run the agent through Agent Evaluation against a real eval set.
5. Deploy to a Model Serving endpoint.

### Assignments

1. **Scenario — First tool-calling agent:** Register one Unity Catalog Function (e.g., a simple lookup or calculation) as a tool, and build an agent that correctly decides when to call it vs. answer directly.
2. **Scenario — Multi-tool composition:** Extend the agent from Assignment 1 to also use a vector search retriever (Section 4) or a Genie conversation (Section 2) as a second tool, and test it with questions that require each tool separately, plus one question that requires both.
3. **Scenario — Evaluation before trust:** Build a small eval set (10-15 question/expected-answer pairs) covering both easy and edge cases, run the agent through Agent Evaluation, and document at least one failure it surfaced.
4. **Scenario — Tracing and root-cause:** Deliberately break one tool (e.g., point it at the wrong table) and use MLflow tracing to identify exactly which step caused the wrong final answer, without re-reading the whole agent code from scratch.
5. **Scenario — Deployment and monitoring:** Deploy the agent to a Model Serving endpoint, send it a few live requests, and show how you'd monitor its behavior (latency, error rate, or a sample of logged interactions) after deployment.

---

*End of document.*
