# Congress Twin — Interactive Intelligent Planner: Product Plan

**Vision:** Transform Congress Twin from a **task viewer** into an **intelligent, interactive congress planner** where users add, edit, delete, and manage tasks from the dashboard; push changes to MS Planner; use previous-year data as templates with simulation-driven recommendations; and get impact analysis, dependency lens, and chat-driven insights.

---

## Table of Contents

1. [Anatomy of the Plan](#1-anatomy-of-the-plan)
2. [Interactive Task Management](#2-interactive-task-management)
3. [MS Planner Integration: Hard Push & Publish](#3-ms-planner-integration-hard-push--publish)
4. [Previous-Year Template & Simulation](#4-previous-year-template--simulation)
5. [Dependency, Critical Path & Impact Analysis](#5-dependency-critical-path--impact-analysis)
6. [Recommended Assignees & Slippage Impact](#6-recommended-assignees--slippage-impact)
7. [Transaction Management & Concurrency](#7-transaction-management--concurrency)
8. [Visualizations & Dashboards](#8-visualizations--dashboards)
9. [Multi-Plan & Attention Engine](#9-multi-plan--attention-engine)
10. [Graph & Impact Engine (MVP → Enterprise)](#10-graph--impact-engine-mvp--enterprise)
11. [Chat Interface](#11-chat-interface)
12. [Implementation Phases](#12-implementation-phases)

---

## 1. Anatomy of the Plan

```
Plan (e.g. UC31 Congress 2026)
├── Buckets (workstreams / phases)
│   ├── Registration & Logistics
│   ├── Behaviour Strategy
│   ├── Booth Development
│   ├── Venue & Logistics
│   ├── Speaker Management
│   └── …
│   └── Tasks (each with fields 1, 2, 3… and optional subtasks)
│       ├── Task A
│       │   ├── Fields: title, status, due, assignees, priority, …
│       │   └── Subtasks (checklist items; multiple per task)
│       │       ├── Subtask 1
│       │       ├── Subtask 2
│       │       └── …
│       ├── Task B
│       └── …
```

- **Plan:** One congress/event (e.g. `uc31-plan`). Multiple plans can run in parallel.
- **Bucket:** Workstream or phase (e.g. Registration & Logistics, Booth Development). Already modeled as `bucketId` / `bucketName` on tasks.
- **Task:** Single unit of work with full MS Planner–like fields (title, status, due, start, assignees, priority, description, etc.).
- **Subtasks:** One-to-many per task. Stored as **checklist items** in `planner_task_details.checklist_items`. Each subtask: id, title, isChecked, orderHint.

**Data model alignment:**  
- Tasks: `planner_tasks` + `planner_task_details`.  
- Subtasks: `planner_task_details.checklist_items` (array of `{ id, title, isChecked?, orderHint? }`).  
- Buckets: derived from tasks (`bucketId`, `bucketName`); optionally persist `planner_buckets` if we need bucket-only CRUD.

---

## 2. Interactive Task Management

Users must be able to **add, edit, delete, and manage** tasks (and subtasks) **from the dashboard**, not only view them.

| Capability | Description |
|------------|-------------|
| **Create task** | New task with title, bucket, due/start, assignees, priority. Optional: run “recommended assignee” and “impact of this task” before save. |
| **Edit task** | Update any field (title, dates, assignees, status, bucket, etc.). Before save: show **impact of this edit** (downstream tasks, critical path, slippage). |
| **Delete task** | Soft-delete or hard delete with confirmation; show impact on dependencies and critical path. |
| **Create subtask** | Add checklist item to a task; show impact (e.g. “adds ~X days to task duration” if we have estimates). |
| **Edit/delete subtask** | Edit or remove checklist items; reflect in task completion (e.g. percent complete from checked subtasks). |
| **Reorder tasks/subtasks** | Order hint / drag-and-drop for tasks within bucket and subtasks within task. |

**UX:** Inline create/edit in list, or slide-over / modal for task detail with full fields and subtask list. All mutations go through API; then optional **Publish to MS Planner** (see §3).

---

## 3. MS Planner Integration: Hard Push & Publish

- **Current:** Sync *from* MS Planner (read). Seed/simulated data when Graph not configured.
- **Target:** **Hard push** of local changes *to* MS Planner when user chooses.

| Feature | Description |
|---------|-------------|
| **Publish to Planner** | Explicit “Publish” action: push current plan state (buckets, tasks, assignments, dependencies) to MS Planner via Graph API. |
| **Conflict handling** | If Planner was updated elsewhere, show diff and let user choose: overwrite Planner, merge, or discard local. |
| **Scoped push** | Option to “Publish only this bucket” or “Publish only changed tasks” to reduce noise. |
| **Publish status** | Show last publish time and “Unpublished changes” count (from `plan_sync_state` + dirty flag). |

**API:**  
- `POST /api/v1/planner/publish/{plan_id}` — full push.  
- Optional: `POST /api/v1/planner/publish/{plan_id}?scope=bucket&bucket_id=...` for scoped push.  
**Backend:** Extend `graph_client` with `create_plan`, `create_bucket`, `create_task`, `update_task`, `delete_task`, `create_dependency` (Graph API), and call from a new `publish_service` that reconciles DB → Graph.

---

## 4. Previous-Year Template & Simulation

- **Load previous year:** User selects a prior congress plan (e.g. “UC30 2025”) as template.
- **Create plan from template:** Copy plan metadata, buckets, tasks, and assignments into a **new** plan (e.g. “UC31 2026”). Create corresponding DB entries (and optionally MS Planner plan later).
- **Run simulation on new plan:** After templating, run **Monte Carlo** (and optionally Markov) to:
  - Propose **ideal assignments** (who should do what based on previous-year success and occupancy).
  - Suggest **best possible way to complete** (order, dates, risk mitigation) based on previous-year learnings and variance.
- **Surface in UI:** After “Create from template”, show:
  - New plan with all tasks/buckets/assignments.
  - **Dependency lens** and **critical path** for high-stake tasks.
  - Simulation summary: “Recommended assignees”, “Suggested start/due dates”, “Risks from last year”.

**Data:**  
- Historical plans in DB (e.g. `planner_plans` with `congress_date`); tasks in `planner_tasks`.  
- “Template from plan” = copy `planner_plans` row (new id), copy all `planner_tasks` and `planner_task_dependencies` (and details) with new `planner_plan_id`.  
- Simulation: existing `monte_carlo_simulator` + `historical_analyzer`; add “recommended assignees” from historical completion by assignee/bucket.

**API:**  
- `POST /api/v1/planner/plans/from-template` — body: `{ source_plan_id, new_plan_id, name, congress_date }`.  
- `POST /api/v1/planner/plans/{plan_id}/run-template-simulation` — run Monte Carlo + assignment recommendations; return suggestions and critical path.

---

## 5. Dependency, Critical Path & Impact Analysis

- **Dependency lens:** Already partially there; enhance to show **upstream/downstream** clearly and **impact statement** (“If this task slips by X days, N downstream tasks…”).
- **Critical path:** Longest dependency chain; highlight **high-stake tasks** on critical path.
- **Impact of a change:** For any **edit** (date, assignee, new subtask, delete task):
  - Compute **affected tasks** (downstream, and optionally upstream if predecessors shift).
  - Show **impact summary**: “Shifting this due date by +3 days will delay 2 downstream tasks and move critical path end by ~2 days.”
  - **Confirmation:** Require user to **confirm** after displaying possible impacts before applying the edit.

**Implementation:**  
- Use **graph** (NetworkX for MVP, §10) to compute downstream/impact.  
- API: `GET /api/v1/planner/tasks/{plan_id}/impact-preview` — body: proposed change (task_id, field, new_value); response: affected task ids, new critical path end, suggested message for user.  
- After user confirms: apply update; optionally call impact again for “what changed” summary.

---

## 6. Recommended Assignees & Slippage Impact

- **Recommended assignees:** When creating/editing a task, show **recommended users** based on:
  - **Occupancy** (current workload so we don’t over-assign).
  - **Previous success** (historical completion time / quality for similar bucket/task type).
- **Slippage impact:** If a task is delayed (or user changes due date):
  - Show **how it would impact** downstream tasks and critical path (same as §5).
- **During edit:** For **any** edit (date, assignee, new subtask), show **impact of this edit** (see §5) before saving.

**Backend:**  
- New endpoint or extend task intelligence: `GET /api/v1/planner/recommended-assignees?plan_id=...&task_id=...&bucket_id=...` using historical_analyzer + current assignments.  
- Slippage/impact: reuse graph-based impact from §5.

---

## 7. Transaction Management & Concurrency

- **Task-level locking:** If a user is **editing** a task, **lock** it so others cannot edit concurrently.
- **Behavior:**  
  - On “Edit task” (or open task for edit): acquire lock (e.g. `task_locks`: plan_id, task_id, user_id, locked_at).  
  - If lock exists for another user: **do not allow edit**; show message “User X is currently editing this task.”  
  - Release lock on save or cancel; optional timeout (e.g. 15 min) to auto-release.
- **Schema:** Table `task_locks(plan_id, task_id, user_id, locked_at)` already present in `init_schema_postgres.sql`.

**API:**  
- `POST /api/v1/planner/tasks/{plan_id}/{task_id}/lock` — acquire (return 409 if locked by someone else).  
- `DELETE /api/v1/planner/tasks/{plan_id}/{task_id}/lock` — release.  
- All task update endpoints check lock before applying.

---

## 8. Visualizations & Dashboards

### 8.1 Gantt Chart (Dependency Overlay)

- **Gantt-style chart** with tasks as bars (start → end), **overlapping** to show dependencies (arrows or links between bars).
- Use existing `probability-gantt` data (start_date, end_date, confidence_percent, variance_days, on_critical_path); add dependency edges for “who depends on whom”.
- **View:** Time on X-axis; tasks/buckets on Y; dependency arcs between bars.

### 8.2 Kanban + Top Attention Dashboard

- **Kanban cards** by status (e.g. Not Started, In Progress, Completed) or by bucket.
- **Top Attention Dashboard** with:
  - **Tasks Completed** (count or list).
  - **In Progress** (count).
  - **At Risk** (count; e.g. overdue or due soon with high dependency risk).
  - **Critical path** with **numerator/denominator** (e.g. “3/5 critical path tasks completed” or “3 of 5 on critical path done”).
- **Congress Timeline:** **Countdown** — “Number of days to go” until congress date (from plan’s `congress_date`).

### 8.3 Status, Severity, Recommended Assignees

- **Status:** notStarted, inProgress, completed (and optionally custom).
- **Severity:** From risk engine (e.g. red / yellow / amber / green) for “why attention” and “risk”.
- **Recommended assignees** on card/list: show “Recommended: Alice, Bob” based on occupancy and previous success.

### 8.4 Workstream Progress

- **Workstream = Bucket.** Per bucket, show:
  - Name (e.g. “Registration & Logistics”, “Behaviour Strategy”, “Booth Development”).
  - **Bar** (percentage completion) for that bucket (e.g. 70%).
- Aggregate from tasks in that bucket (e.g. % complete = avg(percentComplete) or weighted by subtasks).

### 8.5 Task List View

- **Color coding** by risk/attention: red, yellow, amber, green (from risk/severity).
- **Overlapping assignees** (e.g. show avatars or names; highlight if over-assigned).
- **Due date** and **“why attention”** (blocked, overdue, due soon, on critical path).
- **Risk/signal icon** (red / yellow / amber / green) per task.

---

## 9. Multi-Plan & Attention Engine

- **Multiple plans:** Users can have **multiple plans** (e.g. UC31, UC32, regional events).  
- **Plans list:** List/card view of **current running plans** with:
  - Plan name, congress date.
  - **Attention Engine** summary per plan:
    - Number of plans (e.g. “3 active plans”).
    - **Percent complete** (overall).
    - **Number of assignees** (or “assignees with overload”).
    - High-level details (blockers count, overdue count, critical path status).
- **Card view:** Each plan is a card; click to drill into that plan’s dashboard.

**API:**  
- `GET /api/v1/planner/plans` — list plans (from `planner_plans`).  
- `GET /api/v1/planner/attention-summary` — for all plans or for a list of plan_ids: percent complete, assignee count, blocker/overdue/critical-path counts per plan.

---

## 10. Graph & Impact Engine (MVP → Enterprise)

- **MVP:** Use **NetworkX** (or similar in-memory graph) to:
  - Build task dependency graph (nodes = tasks, edges = depends_on).
  - Compute critical path, downstream impact, “what if this task slips”.
  - Serve impact preview and dependency lens.
- **Later:** Migrate to **Neo4j** or **Amazon Neptune** for enterprise scale, richer queries, and persistence of graph.

**Impact analysis (confirm before apply):**  
- When user proposes a change (edit date, assignee, add/delete task or subtask), backend computes impact (affected tasks, critical path change).  
- Return to frontend; frontend shows **“This change will impact: … Do you want to proceed?”**  
- On confirm, apply change and optionally show “Impact applied” summary.

---

## 11. Chat Interface

- **Welcome:** When user opens chat, show **possible critical path actions for today** (e.g. “3 tasks on critical path due this week”).
- **Query data:** Users can **ask questions** in natural language, e.g.:
  - “Which tasks are blocked?”
  - “What’s the impact of delaying Task X by 2 days?”
  - “Who is recommended for the Booth Development tasks?”
- **Intent-based suggestions:** In the chat input area, provide **pre-loaded completion suggestions** (intent-based) so users can quickly probe:
  - Tasks, impacts, assignees, critical path, overdue, blockers, simulation results, etc.
- **Backend:** Search/query layer over tasks, dependencies, attention dashboard, simulation results; optional LLM for NL → structured query (or rule-based intents for MVP).

---

## 12. Implementation Phases

### Phase 1 — Interactive CRUD & Locks (Weeks 1–2)

- Task/subtask **create, update, delete** from API and dashboard.
- **Task-level locks** (acquire/release, show “User X is editing”).
- **Impact preview** (simple: downstream task count + critical path message) with **confirm before apply** on edit.

### Phase 2 — Publish & Template (Weeks 2–3)

- **Publish to MS Planner** (full push; Graph API create/update tasks and buckets).
- **Previous-year template:** “Create plan from template” (copy plan + tasks + deps); **run simulation** and show **recommended assignees** and **critical path / dependency lens** for the new plan.

### Phase 3 — Visualizations & Multi-Plan (Weeks 3–5)

- **Gantt** with dependency overlay (use probability-gantt + dependency edges).
- **Kanban** + **Top Attention Dashboard** (Completed / In Progress / At Risk / Critical path numerator/denominator).
- **Congress countdown** (days to go).
- **Workstream progress bars** (per-bucket %).
- **Task list** with color coding, assignees, due date, risk icons (red/amber/yellow/green).
- **Multi-plan card view** and **Attention Engine** summary (plans, % complete, assignees).

### Phase 4 — Intelligence & Chat (Weeks 5–7)

- **Recommended assignees** (occupancy + historical success) on create/edit task.
- **Slippage impact** and **edit impact** fully wired with graph (NetworkX).
- **Chat interface:** welcome with critical path actions; intent-based suggestions; query tasks, impacts, assignees, simulation.

### Phase 5 — Scale & Polish (Weeks 7–8)

- Optional: **Neo4j/Neptune** for graph persistence and scale.
- Conflict handling for Publish (merge/overwrite).
- Scoped publish (bucket or changed tasks only).
- Performance and UX polish.

---

## Summary Table

| Area | Key deliverables |
|------|--------------------|
| **Anatomy** | Plan → Bucket → Task → Subtasks (checklist); multi-plan support |
| **Interactive** | Add / edit / delete tasks and subtasks from dashboard; impact preview + confirm |
| **MS Planner** | Hard push / Publish; optional scoped publish; conflict handling |
| **Template** | Load previous year; create plan from template; run simulation; recommended assignees + critical path |
| **Dependency & impact** | Dependency lens; critical path; impact of edit/slippage; confirm before apply |
| **Concurrency** | Task-level locks; “User X is editing”; lock release on save/cancel |
| **Visuals** | Gantt with deps; Kanban; Attention (Completed/In Progress/At Risk/CP); countdown; workstream bars; task list colors & risk icons |
| **Multi-plan** | Plan list; Attention Engine card view (plans, % complete, assignees) |
| **Graph** | NetworkX MVP → Neo4j/Neptune later for impact and dependencies |
| **Chat** | Critical path actions; query data; intent-based suggestions; optional Malloy/semantic layer (see [CHAT_SEMANTIC_LAYER_DESIGN.md](./CHAT_SEMANTIC_LAYER_DESIGN.md)) |

This plan keeps the existing data model (tasks, buckets, checklist as subtasks, task_locks) and layers interactive management, publish, template, simulation, impact analysis, and chat on top of it.
