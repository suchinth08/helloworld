# Congress Twin — Backend API reference

Base URL: `http://<host>:8010`  
All request/response bodies are JSON unless noted.

---

## Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check. Returns status and service name. |

---

## Plans and tasks (plan management)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/planner/plans` | List all plans (from DB and seed data). |
| GET | `/api/v1/planner/plans/{plan_id}/buckets` | Get buckets (workstreams) for a plan. |
| GET | `/api/v1/planner/tasks/{plan_id}` | Get full task list for a plan. |
| GET | `/api/v1/planner/tasks/{plan_id}/{task_id}` | Get a single task with details (checklist, references, dependencies). |
| POST | `/api/v1/planner/plans/{plan_id}/tasks` | Create a new task in the plan. |
| PATCH | `/api/v1/planner/plans/{plan_id}/tasks/{task_id}` | Partially update a task. |
| DELETE | `/api/v1/planner/plans/{plan_id}/tasks/{task_id}` | Delete a task. |

---

## Subtasks (checklist items)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/planner/plans/{plan_id}/tasks/{task_id}/subtasks` | Add a subtask (checklist item) to a task. |
| PATCH | `/api/v1/planner/plans/{plan_id}/tasks/{task_id}/subtasks/{subtask_id}` | Update a subtask. |
| DELETE | `/api/v1/planner/plans/{plan_id}/tasks/{task_id}/subtasks/{subtask_id}` | Delete a subtask. |

---

## Task intelligence and dependencies

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/planner/tasks/{plan_id}/{task_id}/intelligence` | Get AI-driven intelligence for a task (Monte Carlo, Markov, dependency risks, reassignment suggestions). |
| GET | `/api/v1/planner/tasks/{plan_id}/dependencies/{task_id}` | Get upstream/downstream dependencies and impact for a task. |
| GET | `/api/v1/planner/execution-tasks/{plan_id}` | Get tasks with risk badges (blocked, blocking, at risk, overdue) and dependency counts. |
| POST | `/api/v1/planner/plans/{plan_id}/tasks/{task_id}/impact` | Analyze impact of proposed task changes on downstream tasks. |

---

## Attention and critical path

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/planner/attention-dashboard/{plan_id}` | What needs attention: blockers, overdue, due next 7 days, critical path due next, recently changed. |
| GET | `/api/v1/planner/critical-path/{plan_id}` | Longest dependency chain (critical path). |
| GET | `/api/v1/planner/milestone-analysis/{plan_id}` | Milestone/event-date view: tasks before event date and at-risk tasks (due after event). Query: `event_date` (ISO). |
| GET | `/api/v1/planner/changes-since-sync/{plan_id}` | Tasks modified since last sync (for “changes since publish” panel). |

---

## Sync, publish, seed, and link

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/planner/sync/{plan_id}` | Trigger sync from MS Planner or upsert seed data when Graph not configured. |
| POST | `/api/v1/planner/plans/{plan_id}/publish` | Publish plan to MS Planner (MVP: validates and returns success). |
| POST | `/api/v1/planner/seed` | Seed DB with Congress event data for a plan (bootstrap). Query: `plan_id`. |
| GET | `/api/v1/planner/plan-link` | Get optional direct link to open the plan in MS Planner. Query: `plan_id`. |

---

## Chat

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/planner/chat` | Natural-language chat: intent-based routing (attention, critical path, workload, impact, task list, etc.). Query: `plan_id`. Body: `{ "message": "..." }`. |

---

## Templates

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/planner/template/sources` | List available template plans (e.g. congress-2022, 2023, 2024). |
| POST | `/api/v1/planner/template` | Create a new plan from a template; optional simulation. Body: target_plan_id, source_plan_id, congress_date, run_simulation. |

---

## Task locking (collaborative edit)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/planner/plans/{plan_id}/tasks/{task_id}/lock` | Acquire lock for editing a task. Query: `user_id`. |
| DELETE | `/api/v1/planner/plans/{plan_id}/tasks/{task_id}/lock` | Release task lock. Query: `user_id`. |
| GET | `/api/v1/planner/plans/{plan_id}/tasks/{task_id}/lock` | Get lock status for a task. |

---

## Advanced views (probability, mitigation, insights)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/planner/probability-gantt/{plan_id}` | Tasks with start/end, confidence %, variance for Probability Gantt. |
| GET | `/api/v1/planner/mitigation-feed/{plan_id}` | Agent interventions / mitigation feed for Commander view. |
| GET | `/api/v1/planner/veeva-insights/{plan_id}` | KOL alignment and staff fatigue insights (simulated). |
| GET | `/api/v1/planner/monte-carlo/{plan_id}` | Run Monte Carlo: P(on-time), percentile end dates, risk tasks, agent suggestions. Query: `n_simulations`, `event_date`, `seed`. |

---

## Alerts and human-in-the-loop (external events, proposed actions)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/planner/alerts/{plan_id}` | Dashboard alerts: external events and pending agent proposed actions. |
| GET | `/api/v1/planner/proposed-actions/{plan_id}` | List agent proposed actions for human approval. Query: `status` (pending, approved, rejected). |
| POST | `/api/v1/planner/proposed-actions/{plan_id}/{action_id}/approve` | Human approves proposed action; agent applies re-adjustment. Query: `decided_by`. |
| POST | `/api/v1/planner/proposed-actions/{plan_id}/{action_id}/reject` | Human rejects proposed action. Query: `decided_by`. |
| POST | `/api/v1/planner/external-events/{plan_id}` | Ingest external event (e.g. webhook). Creates alert and agent proposals. Body: event_type, title, description, severity, affected_task_ids, payload. |
| DELETE | `/api/v1/planner/external-events/{plan_id}/{event_id}` | Delete an external event and its proposed actions. |
| DELETE | `/api/v1/planner/proposed-actions/{plan_id}/{action_id}` | Delete a single proposed action. |

---

## Streaming

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/planner/stream` | SSE stream: plan vs reality and agent updates (simulated). Query: `plan_id`. |

---

## Import

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/import/csv` | Import CSV file with tasks. Expects columns: ID, Bucket, Label, Task, Start Date, Due Date, etc. Query: `plan_id`. Body: multipart file upload. |

---

## Simulation (Monte Carlo, Markov, cost, historical)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/simulation/monte-carlo` | Run Monte Carlo simulation (iterations, DAG, resource contention). Returns percentiles, critical path probability, bottlenecks, risk heatmap. Body: plan_id, n_iterations, historical_plan_ids. |
| GET | `/api/v1/simulation/markov-analysis` | Get Markov chain analysis: state transition probabilities, expected completion time. Query: `plan_id`, `task_id`. |
| POST | `/api/v1/simulation/cost-analysis` | Compute multi-objective cost breakdown with configurable weights. Body: plan_id, weights. |
| GET | `/api/v1/simulation/historical-insights` | Get historical insights: duration bias, bottleneck patterns, resource profiles, risk patterns. Query: `plan_id`, `historical_plan_ids`. |

---

## Backend services (internal, used by APIs)

| Service | Role |
|---------|------|
| **planner_service** | Plan/task CRUD, sync, seed, get_tasks_for_plan, get_attention_dashboard, get_critical_path, get_milestone_analysis, get_execution_tasks, get_changes_since_sync, sync_planner_tasks, seed_congress_plan. |
| **chat_service** | handle_chat_message: intent-based dispatch (attention, critical_path, workload, impact, task_list, dependencies, milestone, monte_carlo, summary). |
| **chat_intent** | extract_intent: LLM (Groq/OpenAI) or regex fallback for intent + entities. |
| **impact_analyzer** | analyze_edit_impact: impact of task changes on downstream tasks. |
| **task_intelligence** | get_task_intelligence: Monte Carlo, Markov, dependency risks, reassignment suggestions. |
| **cost_function** | compute_total_cost: cost analysis with weights. |
| **monte_carlo_simulator** | run_simulation, run_monte_carlo: P(on-time), percentiles, risk tasks. |
| **markov_chain_tracker** | get_markov_analysis: state transition probabilities. |
| **historical_analyzer** | get_historical_insights: duration bias, bottlenecks, resource profiles. |
| **template_service** | list_historical_plans, create_plan_from_template. |
| **publish_service** | publish_plan_to_planner. |
| **lock_service** | acquire_lock, release_lock, get_lock. |
| **csv_importer** | import_csv_to_planner_tasks. |
| **planner_repo** (db) | get_planner_tasks, upsert_planner_tasks, list_planner_plans, get_planner_task_dependencies, ensure_postgres_schema, etc. |
| **events_repo** (db) | external_events, agent_proposed_actions, get_alerts, get_proposed_actions, approve/reject/delete actions. |
