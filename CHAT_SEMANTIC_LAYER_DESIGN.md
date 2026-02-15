# Congress Twin — Intelligent Chat: Semantic Layer Design

**Phase 1 (Hybrid) implemented:** Intent + LLM extraction, full intent catalog, trace store. See `chat_intent.py`, `chat_service.py`, `chat_trace_store.py` and config `CHAT_LLM_API_KEY`, `CHAT_LLM_MODEL`, `CHAT_LLM_BASE_URL`, `CHAT_TRACE_STORE_PATH`.

**Goal:** Make the planner chat intelligent by mapping user natural language to the **data fabric** (plans, tasks, dependencies, attention, critical path, impact) through a **schematic/semantic layer**, with optional **Malloy** (or similar) for composable analytics.

---

## 1. Current State

- **Chat:** `POST /api/v1/planner/chat?plan_id=...` → `chat_service.handle_chat_message(plan_id, message)`.
- **Logic:** Intent-based **regex** patterns; no LLM, no semantic model.
- **Intents today:** attention, critical path, workload/assignees, impact of delaying task X, default summary.
- **Data access:** Direct calls to `planner_service` (e.g. `get_attention_dashboard`, `get_critical_path`, `get_tasks_for_plan`) and `impact_analyzer`.

**Limitation:** Fragile to phrasing; no “which tasks are blocked by task-005?” or “show me completion by bucket”; no learning from past queries.

---

## 2. Data Fabric (Conceptual Schema)

Congress Twin’s “data fabric” is the set of concepts and APIs that chat should be able to query. Represented as a **logical schema** (for Malloy or for an intent catalog):

| Concept | Source | Key fields / semantics |
|--------|--------|-------------------------|
| **Plans** | `list_plans()` | plan_id, name, congress_date |
| **Tasks** | `get_tasks_for_plan(plan_id)` | id, title, bucketId, bucketName, status, percentComplete, dueDateTime, startDateTime, assignees, assigneeNames |
| **Buckets** | `get_buckets_for_plan(plan_id)` | id, name (workstreams) |
| **Dependencies** | `get_dependencies_for_plan(plan_id)` | (task_id, depends_on_task_id) |
| **Attention** | `get_attention_dashboard(plan_id)` | blockers, overdue, due_next_7_days, critical_path_due_next, recently_changed |
| **Critical path** | `get_critical_path(plan_id)` | task_ids, critical_path (list of tasks) |
| **Execution** | `get_execution_tasks(plan_id)` | tasks with risk_badges, upstream_count, downstream_count, on_critical_path |
| **Impact** | `analyze_edit_impact(plan_id, task_id, changes)` | affected_task_ids, message |
| **Monte Carlo** | `run_monte_carlo(plan_id, ...)` | probability_on_time_percent, percentile_end_dates, risk_tasks |
| **Milestone** | `get_milestone_analysis(plan_id, event_date)` | tasks_before_event, at_risk_tasks |

For a **Malloy** semantic layer we would expose these as **sources** (e.g. `planner_tasks`, `planner_attention`, `planner_critical_path`) over either:
- a **DuckDB** (or SQLite) mirror of planner data refreshed on sync/interval, or  
- **API-backed** views if Malloy supports that (or we generate SQL that our backend translates to API calls).

---

## 3. Option A: Malloy Semantic Layer

### 3.1 Idea

- Define a **Malloy model** (e.g. `semantic_layer.malloy`) that describes:
  - **Sources:** `planner_tasks`, `planner_buckets`, `planner_dependencies`, `planner_attention`, `planner_critical_path`, etc.
- User message → **LLM** (with schema + few-shot traces) → **Malloy query** → **Malloy runtime** → result → natural language response.

### 3.2 Data source for Malloy

- **Option A1 – DuckDB over exported data:**  
  - Periodically (or on demand) export `planner_tasks`, `planner_task_dependencies`, and optionally `planner_plans` from Postgres/SQLite into a **DuckDB** file (or in-memory DB).  
  - Malloy model points to this DuckDB; Malloy runs queries against it.
- **Option A2 – SQLite attach:**  
  - Use existing SQLite (e.g. `congress_twin.db`) and **attach** it in DuckDB; define Malloy model over that schema (same as fmcg-mroi pattern).

### 3.3 Example Malloy schema (conceptual)

```malloy
// semantic_layer.malloy (conceptual)
// Connection: DuckDB with congress_twin SQLite attached or exported tables.

source: planner_tasks is table('planner_tasks') {
  primary_key: planner_task_id
  measure:
    task_count is count()
    completed_count is count() { where: status = 'completed' }
    completion_pct is completed_count / task_count * 100
}

source: planner_buckets is table('planner_buckets') {
  primary_key: id
}

source: planner_attention is from(
  // Could be a view or API-backed; if DuckDB only, materialize from tasks + deps
  planner_tasks + join to planner_dependencies
) {
  // blockers, overdue, due_next_7_days as dimensions/measures
}
```

Queries such as “completion by bucket”, “tasks due next week”, “blocked tasks” would be expressed as Malloy and run by the runtime.

### 3.4 Chat flow (Malloy path)

1. **User:** “What’s our completion by workstream?”
2. **Intent / entity extraction (optional):** plan_id from context; “completion by workstream” → analytical.
3. **Malloy architect (LLM):** Given Malloy schema + similar past traces (e.g. “completion by bucket” → `run: planner_tasks -> { group_by: bucket_name, aggregate: completion_pct }`), generate Malloy query.
4. **Critic (optional):** Validate Malloy for logical/semantic errors; loop back to architect if needed.
5. **Executor:** Run Malloy query (DuckDB + Malloy runtime); get result set.
6. **Response:** Format result (e.g. table or bullets) and optionally add a short NL summary (LLM or template).

### 3.5 Pros and cons

- **Pros:** Single semantic model; rich, composable analytics; consistent with fmcg-mroi; good for “slice/dice” questions.
- **Cons:** Requires data export or attach + schema sync; Malloy dependency; operational questions (e.g. “impact of delaying task X”) may still need to hit existing APIs unless modeled in Malloy.

---

## 4. Option B: Intent + LLM-to-API “Query” Layer (No Malloy)

### 4.1 Idea

- Keep the **data fabric** as the **existing Congress Twin APIs** (no new DB).
- Introduce a **semantic layer** as:
  - **Intent catalog:** each intent maps to one or more service calls (e.g. `attention` → `get_attention_dashboard(plan_id)`).
  - **LLM:** Maps user message → **intent + entities** (plan_id, task_id, slippage_days, event_date, etc.).
  - **Backend:** Executes the corresponding API(s), then formats the result into a **text** (and optional structured `data`) for the client.

### 4.2 Intent catalog (extended)

| Intent | API(s) | Entities | Example user phrase |
|--------|--------|----------|---------------------|
| attention | get_attention_dashboard | plan_id | “What needs attention?”, “Blocked tasks” |
| critical_path | get_critical_path | plan_id | “Critical path”, “Longest chain” |
| workload | get_tasks_for_plan + aggregate by assignee | plan_id | “Who is overloaded?”, “Workload by person” |
| impact | analyze_edit_impact / analyze_slippage_impact | plan_id, task_id, slippage_days | “Impact of delaying task-005” |
| task_list | get_tasks_for_plan (optional filters) | plan_id, status, bucket | “Tasks in progress”, “Tasks in Build bucket” |
| dependencies | get_dependencies | plan_id, task_id | “What depends on task-003?”, “Upstream of task-007” |
| milestone | get_milestone_analysis | plan_id, event_date | “Tasks at risk for go-live”, “Milestone by March 1” |
| monte_carlo | run_monte_carlo | plan_id, event_date | “Probability we finish on time”, “Monte Carlo” |
| summary | get_tasks_for_plan + counts | plan_id | “How many tasks?”, “Plan summary” |

### 4.3 Chat flow (intent path)

1. **User:** “What’s blocking us today?”
2. **LLM (intent + entities):** Input: message + current plan_id. Output: `{ "intent": "attention", "entities": { "plan_id": "uc31-plan" } }`.
3. **Backend:** Call `get_attention_dashboard(plan_id)`; get blockers, overdue, due_next_7_days.
4. **Formatter:** Turn result into readable text (and optionally keep `data` for UI).
5. **Optional:** Store (user_query, intent, response) as **trace** for few-shot later or RAG.

### 4.4 Optional: “Query DSL” for complex questions

- For questions that need **multiple** APIs (e.g. “Critical path and who’s on it”), the LLM can output a small **structured query** instead of a single intent, e.g.  
  `{ "ops": [ { "op": "critical_path", "plan_id": "uc31-plan" }, { "op": "task_details", "task_ids": "<from critical_path>" } ] }`.  
- Backend interprets this DSL, runs the ops in order (with outputs feeding inputs where needed), then formats the combined result.

### 4.5 Pros and cons

- **Pros:** No new DB or Malloy; reuses all existing APIs; fast to implement; works for operational and impact questions.
- **Cons:** Less flexible for arbitrary ad-hoc analytics than a full Malloy model; intent catalog must be maintained and extended.

---

## 5. Hybrid (Recommended Direction)

- **Phase 1 – Intent + LLM (Option B):**
  - Add an **LLM** step for intent + entity extraction (plan_id, task_id, etc.).
  - Expand the **intent catalog** to cover dependencies, milestone, Monte Carlo, task list with filters.
  - Optional: **RAG over past traces** (e.g. store successful user_query → intent + params → response) to improve robustness.
  - Optional: **Structured “query”** (small DSL) for multi-step questions.
  - **Deliverable:** Chat that reliably maps many phrasings to the right API and returns clear, formatted answers.

- **Phase 2 – Optional Malloy (Option A):**
  - If you need **analytical** questions (“completion by bucket”, “trend over time”, “compare plans”), add:
    - **Export:** Snapshot of planner_tasks (and optionally dependencies) to DuckDB (or SQLite attached in DuckDB).
    - **Malloy model:** Define `semantic_layer.malloy` over that schema.
    - **Router:** For “analytical” intent (or when intent is unclear but message looks like a slice/dice question), route to **Malloy architect** → run Malloy → format result; otherwise keep using intent → API.
  - **Deliverable:** One chat that handles both operational (intent → API) and analytical (Malloy) questions.

---

## 6. Implementation Outline

### Phase 1 (Intent + LLM, no Malloy)

1. **Dependencies:** Add LLM dependency (e.g. `langchain-groq`, `openai`, or same as fmcg-mroi).
2. **Intent + entity extraction:**
   - Prompt: “Given the user message and current plan_id, return JSON: intent, entities (plan_id, task_id, slippage_days, event_date, bucket_id, status).”
   - Intents: attention, critical_path, workload, impact, task_list, dependencies, milestone, monte_carlo, summary.
3. **Chat service:**
   - Replace (or complement) regex with LLM-based intent.
   - Map intent + entities → existing planner_service / impact_analyzer / monte_carlo calls.
   - Format response (text + optional data).
4. **Optional trace store:** SQLite table (user_query, intent, entities, response_snippet); use for few-shot in prompt or RAG.
5. **Frontend:** No change to API contract; optional display of “intent” or “sources” for transparency.

### Phase 2 (Optional Malloy)

1. **Export/sync:** Job or endpoint that writes `planner_tasks` (and optionally dependencies) to DuckDB or to a SQLite file that DuckDB attaches.
2. **Malloy model:** Write `semantic_layer.malloy` for congress_twin (sources over tasks, buckets, aggregates).
3. **Malloy runner:** Thin module (like fmcg-mroi’s `malloy_runner.py`) that runs Malloy against that DB.
4. **Router in chat:** If intent is “analytical” or “unknown” and message looks like a query (e.g. “by bucket”, “count”, “group”), call Malloy architect + runner; else use intent → API.
5. **Critic loop (optional):** Like fmcg-mroi, add a critic step that validates generated Malloy and retries once if needed.

---

## 7. Summary

| Approach | Data fabric | User message → | Output |
|----------|-------------|----------------|--------|
| **Current** | Planner APIs | Regex → intent | Single API call, text |
| **Option B (recommended first)** | Same APIs | LLM → intent + entities → API(s) | Formatted text + optional data |
| **Option A (Malloy)** | DuckDB (export of planner data) + Malloy schema | LLM → Malloy query → runtime | Result set → formatted text |
| **Hybrid** | APIs + DuckDB/Malloy for analytics | Router → intent/API or Malloy path | Same as above, best of both |

**Recommendation:** Implement **Phase 1 (intent + LLM)** to make chat intelligent and robust without new infrastructure; add **Phase 2 (Malloy)** later if you need rich analytical queries over the same data fabric.
