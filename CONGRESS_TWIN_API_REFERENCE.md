# Congress Twin API Reference

Base URL: `http://localhost:8010` (or `NEXT_PUBLIC_CONGRESS_TWIN_API_URL` in frontend).

All planner endpoints are under **`/api/v1/planner`**. Default plan ID for simulated data: `uc31-plan`.

**Database:** Set `POSTGRES_HOST` (see `.env.example`) to use your existing PostgreSQL; the app will auto-seed simulated congress tasks and dependencies for the default plan when the DB is empty. Without `POSTGRES_HOST`, SQLite is used with the same simulated data.

---

## Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |

**Response:** `{"status": "ok", "service": "congress-twin"}`

---

## Planner APIs

### 1. Get tasks

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/planner/tasks/{plan_id}` | Task list for a plan (enriched: bucketName, dueDateTime, assignees, assigneeNames) |

**Response:**
```json
{
  "plan_id": "uc31-plan",
  "tasks": [
    {
      "id": "task-001",
      "title": "Stakeholder interviews",
      "bucketId": "...",
      "bucketName": "Discovery",
      "percentComplete": 100,
      "status": "completed",
      "dueDateTime": "2025-01-31T00:00:00+00:00",
      "assignees": ["user-1"],
      "assigneeNames": ["Alex"],
      "lastModifiedAt": "..."
    }
  ],
  "count": 8
}
```

**Errors:** 404 if `plan_id` not found.

---

### 2. Attention dashboard

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/planner/attention-dashboard/{plan_id}` | What needs attention: blockers, overdue, due next 7d, recently changed |

**Response:**
```json
{
  "plan_id": "uc31-plan",
  "blockers": { "count": 5, "tasks": [{ "id", "title", "status", "dueDateTime", "assigneeNames" }] },
  "overdue": { "count": 1, "tasks": [...] },
  "due_next_7_days": { "count": 2, "tasks": [...] },
  "recently_changed": { "count": 1, "tasks": [...] }
}
```

**Errors:** 404 if `plan_id` not found.

---

### 3. Task dependencies

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/planner/tasks/{plan_id}/dependencies/{task_id}` | Upstream/downstream and impact statement for a task |

**Response:**
```json
{
  "task_id": "task-006",
  "upstream": [{ "id", "title", "status", "dueDateTime", "assigneeNames" }],
  "downstream": [{ "id", "title", "status", "dueDateTime", "assigneeNames" }],
  "impact_statement": "If this task slips, 1 downstream task(s) may be impacted."
}
```

**Errors:** 404 if `plan_id` or `task_id` not found.

---

### 4. Critical path

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/planner/critical-path/{plan_id}` | Longest dependency chain (critical path) |

**Response:**
```json
{
  "plan_id": "uc31-plan",
  "critical_path": [
    { "id": "task-001", "title": "...", "status": "completed", "dueDateTime": "..." }
  ],
  "task_ids": ["task-001", "task-002", ...]
}
```

**Errors:** 404 if `plan_id` not found.

---

### 5. Milestone analysis

| Method | Path | Query | Description |
|--------|------|-------|-------------|
| GET | `/api/v1/planner/milestone-analysis/{plan_id}` | `event_date` (optional, ISO) | Tasks before event date and at-risk (due after event) |

**Query:**
- `event_date` — Optional. ISO date/time (e.g. `2025-03-01` or `2025-03-01T12:00:00Z`). Default: 21 days from now.

**Response:**
```json
{
  "plan_id": "uc31-plan",
  "event_date": "2025-02-26T00:00:00+00:00",
  "tasks_before_event": [
    { "id", "title", "status", "dueDateTime", "assigneeNames", "on_critical_path": false }
  ],
  "at_risk_tasks": [
    { "id", "title", "status", "dueDateTime", "assigneeNames", "days_after_event": 5 }
  ],
  "at_risk_count": 4
}
```

**Errors:** 404 if `plan_id` not found. 400 if `event_date` is invalid ISO.

---

### 6. Sync from Planner (Phase 1)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/planner/sync/{plan_id}` | Trigger sync from MS Planner (or upsert Congress seed to DB when no Graph) |
| POST | `/api/v1/planner/seed?plan_id=uc31-plan` | Seed DB with Novartis Congress event data (dev/bootstrap) |

**Response (no Graph — Congress seed upserted to DB):**
```json
{
  "plan_id": "uc31-plan",
  "status": "ok",
  "source": "congress_seed",
  "tasks_synced": 7,
  "message": "Sync completed (congress seed). Set GRAPH_* for live Planner sync."
}
```

**Seed endpoint** `POST /api/v1/planner/seed?plan_id=uc31-plan`: same idea (ensures tables, upserts congress tasks, sets sync state). Response: `{ "plan_id", "status": "ok", "tasks_seeded": 7, "message": "..." }`.

**Attention dashboard** now includes `critical_path_due_next` (tasks on critical path due in next 7 days).

**Response (live Graph):** `source` is `"graph"`, `tasks_synced` is the count from Graph API.

**Response (Graph error):** `status` is `"error"`, `tasks_synced` is `0`, `message` describes the failure.

**Errors:** 404 if `plan_id` not found.

---

### 3b. Changes since sync (publish)

| Method | Path | Description |
|--------|------|--------------|
| GET | `/api/v1/planner/changes-since-sync/{plan_id}` | Tasks modified since previous sync (for "Changes since publish" panel) |

**Response:** `{ "plan_id", "changes": [{ "id", "title", "status", "dueDateTime", "assigneeNames", "lastModifiedAt" }], "count" }`

### 3c. Execution tasks (Dependency Lens)

| Method | Path | Description |
|--------|------|--------------|
| GET | `/api/v1/planner/execution-tasks/{plan_id}` | Tasks with risk badges (blocked, blocking, at_risk, overdue) and upstream_count, downstream_count |

**Response:** `{ "plan_id", "tasks": [{ ...PlannerTask, "risk_badges", "upstream_count", "downstream_count", "on_critical_path" }], "count" }`

### 3d. Plan link (Open in Planner)

| Method | Path | Description |
|--------|------|--------------|
| GET | `/api/v1/planner/plan-link?plan_id=...` | Optional URL to open the plan in MS Planner (when `PLANNER_PLAN_URL` is set) |

**Response:** `{ "plan_id", "url": "" }` (url empty if not configured)

---

## Advanced view (Commander)

### 8. Probability Gantt

| Method | Path | Description |
|--------|------|--------------|
| GET | `/api/v1/planner/probability-gantt/{plan_id}` | Tasks with start/end, confidence %, variance for Probability Gantt |

**Response:** `{ "plan_id": "...", "bars": [{ "id", "title", "status", "start_date", "end_date", "confidence_percent", "variance_days", "on_critical_path" }] }`

### 9. Mitigation feed

| Method | Path | Description |
|--------|------|--------------|
| GET | `/api/v1/planner/mitigation-feed/{plan_id}` | Agent interventions (shifted, updated, flagged) for Commander View |

**Response:** `{ "plan_id": "...", "interventions": [{ "id", "task_id", "task_title", "action", "reason", "at" }] }`

### 10. Veeva insights

| Method | Path | Description |
|--------|------|--------------|
| GET | `/api/v1/planner/veeva-insights/{plan_id}` | KOL alignment and staff fatigue (simulated) |

**Response:** `{ "plan_id", "kol_alignment_score", "kol_alignment_trend", "staff_fatigue_index", "staff_fatigue_trend", "summary", "insights" }`

### 11. SSE stream (Plan vs Reality)

| Method | Path | Description |
|--------|------|--------------|
| GET | `/api/v1/planner/stream?plan_id=...` | Server-Sent Events: snapshot and live updates (simulated) |

**Query:** `plan_id` (optional, default `uc31-plan`). Client uses `EventSource`; each event is JSON in `data:`.

---

### 12. Monte Carlo simulation & agent suggestions

| Method | Path | Query | Description |
|--------|------|-------|--------------|
| GET | `/api/v1/planner/monte-carlo/{plan_id}` | `n_simulations` (default 500), `event_date` (ISO), `seed` | Run Monte Carlo; P(on-time), percentile end dates, risk tasks; **agent_suggestions** (enhancements & modifications) |

**Response:** `plan_id`, `n_simulations`, `event_date`, `probability_on_time_percent`, `percentile_end_dates` (p10, p50, p90), `risk_tasks`, `agent_suggestions` (list of `{ type, priority, title, detail, action_hint }`).

### 13. External events & alerts (data sync / push — external REST API)

External systems (webhooks, ETL, other services) can ingest events via REST.

| Method | Path | Description |
|--------|------|--------------|
| POST | `/api/v1/planner/external-events/{plan_id}` | **External REST API:** Ingest event (flight_cancellation, participant_meeting_cancelled); creates alert and agent proposed re-adjustments (HITL) |
| GET | `/api/v1/planner/alerts/{plan_id}` | Dashboard: external events + pending proposed actions |
| DELETE | `/api/v1/planner/external-events/{plan_id}/{event_id}` | Delete event and all its proposed actions (for testing) |
| DELETE | `/api/v1/planner/proposed-actions/{plan_id}/{action_id}` | Delete a single proposed action (for testing) |

**POST body (external-events):** `event_type` (e.g. `flight_cancellation`, `participant_meeting_cancelled`), optional `title`, `description`, `severity`, `affected_task_ids`, `payload` (e.g. `{ "shift_days": 2 }`).

**Example (external REST call):**
```bash
curl -X POST "http://localhost:8010/api/v1/planner/external-events/uc31-plan" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"flight_cancellation","severity":"medium","payload":{"shift_days":2}}'
```

### 14. Human-in-the-loop (proposed actions)

| Method | Path | Description |
|--------|------|--------------|
| GET | `/api/v1/planner/proposed-actions/{plan_id}` | List agent proposed actions (optional `?status=pending`) |
| POST | `/api/v1/planner/proposed-actions/{plan_id}/{action_id}/approve` | Approve; agent applies re-adjustment (e.g. shift task due date in DB) |
| POST | `/api/v1/planner/proposed-actions/{plan_id}/{action_id}/reject` | Reject proposed action |

---

## Summary table

| # | Method | Path |
|---|--------|------|
| 1 | GET | `/health` |
| 2 | GET | `/api/v1/planner/tasks/{plan_id}` |
| 3 | GET | `/api/v1/planner/attention-dashboard/{plan_id}` |
| 3b | GET | `/api/v1/planner/changes-since-sync/{plan_id}` |
| 3c | GET | `/api/v1/planner/execution-tasks/{plan_id}` |
| 3d | GET | `/api/v1/planner/plan-link?plan_id=...` |
| 4 | GET | `/api/v1/planner/tasks/{plan_id}/dependencies/{task_id}` |
| 5 | GET | `/api/v1/planner/critical-path/{plan_id}` |
| 6 | GET | `/api/v1/planner/milestone-analysis/{plan_id}?event_date=...` |
| 7 | POST | `/api/v1/planner/sync/{plan_id}` |
| 7b | POST | `/api/v1/planner/seed?plan_id=uc31-plan` |
| 8 | GET | `/api/v1/planner/probability-gantt/{plan_id}` |
| 9 | GET | `/api/v1/planner/mitigation-feed/{plan_id}` |
| 10 | GET | `/api/v1/planner/veeva-insights/{plan_id}` |
| 11 | GET | `/api/v1/planner/stream?plan_id=...` |
| 12 | GET | `/api/v1/planner/monte-carlo/{plan_id}?n_simulations=500&event_date=...` |
| 13 | POST | `/api/v1/planner/external-events/{plan_id}` (external REST API) |
| 13b | GET | `/api/v1/planner/alerts/{plan_id}` |
| 13c | DELETE | `/api/v1/planner/external-events/{plan_id}/{event_id}` |
| 13d | DELETE | `/api/v1/planner/proposed-actions/{plan_id}/{action_id}` |
| 14 | GET | `/api/v1/planner/proposed-actions/{plan_id}` |
| 14b | POST | `/api/v1/planner/proposed-actions/{plan_id}/{action_id}/approve` |
| 14c | POST | `/api/v1/planner/proposed-actions/{plan_id}/{action_id}/reject` |
