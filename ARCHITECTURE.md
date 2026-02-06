# Novartis Planner (Congress Twin) — Overall Architecture

This document describes the end-to-end architecture, what was built, and how it maps to the originally assigned tasks. Use it for onboarding and for the architecture + demo deck.

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Users (Browser)                                    │
│  http://localhost:3000/planner  (Base view | Advanced view)                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Frontend (Next.js) — congress-twin/frontend/                                 │
│  • AppShell: sidebar (collapsed = favicon only), nav                          │
│  • Planner page: ViewToggle (Base / Advanced), SyncButton                     │
│  • Base view: PlanOverviewCharts, AttentionDashboard, CriticalPathSection,   │
│               MilestoneLane, DependencyLens, TaskListTable                    │
│  • Advanced view: CommanderView (Monte Carlo, Mitigation Feed, Veeva,        │
│                   Pending Approvals, SSE live status)                         │
│  • AlertsDashboard: external events + pending proposed actions (compact)     │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                    NEXT_PUBLIC_CONGRESS_TWIN_API_URL (default localhost:8010)
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Backend (FastAPI) — congress-twin/src/congress_twin/                        │
│  • Port 8010                                                                 │
│  • /api/v1/planner/* : tasks, attention-dashboard, dependencies,             │
│    critical-path, milestone-analysis, sync, seed, probability-gantt,         │
│    mitigation-feed, veeva-insights, monte-carlo, external-events,            │
│    proposed-actions (approve/reject), alerts, stream (SSE)                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                    Postgres (planner_tasks, plan_sync_state, external_events,
                             agent_proposed_actions)
                                        │
┌─────────────────────────────────────────────────────────────────────────────┐
│  Data Layer                                                                  │
│  • Postgres: planner_tasks, plan_sync_state, planner_tasks.start_date,       │
│              external_events, agent_proposed_actions                         │
│  • Optional: MS Graph (Planner as source of truth for sync)                  │
│  • Optional: Neo4j (for future graph features)                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Components

### 2.1 Frontend (Next.js)

| Component | Purpose |
|-----------|--------|
| **AppShell** | Layout: sidebar (expand/collapse). When collapsed, shows **favicon only** (`/icon`), not the full Novartis logo. Browser tab title: **Novartis Planner**. |
| **Planner page** | Base view vs Advanced view (query `?view=base` / `?view=advanced`). Sync button, plan overview, attention strip, critical path, milestone lane, dependency lens, task table. |
| **AttentionDashboard** | “What needs attention”: Blockers, Overdue, Due next 7 days, Recently changed (from seed/sync relative dates). |
| **CriticalPathSection** | Critical path tasks and impact. |
| **MilestoneLane** | Milestone / Event Date lane (event_date from query or default). |
| **DependencyLens** | Upstream/downstream and impact for a selected task. |
| **AlertsDashboard** | External events + pending agent proposed actions; compact strip at top. |
| **CommanderView** | Advanced: Probability Gantt, Mitigation Feed, Veeva Insights, Monte Carlo suggestions, Pending Approvals (HITL), SSE live status. |

### 2.2 Backend (FastAPI)

- **Planner APIs** (`/api/v1/planner/*`): tasks, attention-dashboard, changes-since-sync, execution-tasks, plan-link, dependencies, critical-path, milestone-analysis, sync, seed, probability-gantt, mitigation-feed, veeva-insights, monte-carlo, external-events (POST/DELETE), proposed-actions (GET/approve/reject/delete), alerts, stream (SSE).
- **Config**: CORS includes `192.168.0.101:3000` and `192.168.0.101:3003` for LAN access.
- **Data**: Reads/writes Postgres (planner_tasks, plan_sync_state, external_events, agent_proposed_actions). Optional MS Graph for sync when configured.

### 2.3 Data (Postgres)

| Table | Purpose |
|-------|--------|
| **planner_tasks** | Task cache (plan_id, task_id, bucket, title, status, percent_complete, due_date, assignees, etc.). |
| **plan_sync_state** | Last sync time per plan. |
| **planner_tasks.start_date** | Start date for scheduling/critical path (migration 003). |
| **external_events** | Ingested events (e.g. flight_cancellation, participant_meeting_cancelled) for alerts. |
| **agent_proposed_actions** | Agent suggestions (e.g. shift due date) with status pending/approved/rejected; optional link to external_event_id. |

---

## 3. Data Flow (Summary)

1. **Sync**: POST `/api/v1/planner/sync/{plan_id}` — with Graph configured, pulls from MS Planner; without Graph, uses congress seed data and upserts to DB. Updates plan_sync_state.
2. **Seed**: POST `/api/v1/planner/seed` — ensures tables, upserts congress tasks (task-001…015), sets sync state. Used for “Due next 7 days”, “Critical path due next”, “Recently changed” with relative dates.
3. **External events**: POST `/api/v1/planner/external-events/{plan_id}` — ingest event; backend can create agent_proposed_actions (e.g. shift_days). Alerts dashboard shows events + pending actions.
4. **HITL**: Approve/Reject proposed actions via API; approve applies re-adjustment (e.g. update task due date in DB).
5. **Monte Carlo**: GET `/api/v1/planner/monte-carlo/{plan_id}` — simulations; agent suggestions surface in Advanced view.

---

## 4. Task Coverage (Assigned vs Implemented)

| # | Assigned task | Status | Notes |
|---|----------------|--------|--------|
| 1 | MS Planner as source of truth | ✅ Supported | Sync uses Graph when credentials set; otherwise seed/simulated data. |
| 2 | Sync / cache in Postgres | ✅ Done | plan_sync_state, planner_tasks; sync and seed APIs. |
| 3 | Dependency Lens | ✅ Done | Upstream/downstream + impact; DependencyLens component. |
| 4 | Milestone / Event Date lane | ✅ Done | MilestoneLane, milestone-analysis API. |
| 5 | “What needs attention” strip | ✅ Done | AttentionDashboard: blockers, overdue, due next 7d, recently changed. |
| 6 | Critical path | ✅ Done | CriticalPathSection, critical-path API. |
| 7 | Blockers | ✅ Done | Part of attention-dashboard and UI. |
| 8 | External events (REST ingest) | ✅ Done | POST external-events, DELETE event and actions. |
| 9 | Human-in-the-loop (approve/reject) | ✅ Done | proposed-actions, approve/reject APIs; PendingApprovals in Advanced view. |
| 10 | Monte Carlo + agent suggestions | ✅ Done | monte-carlo API, MonteCarloSuggestions in Advanced view. |
| 11 | Seed data (Congress, due next 7d, critical path due next, recently changed) | ✅ Done | Seed script/API; relative dates for task-004–007. |
| 12 | Alerts (events + pending actions) | ✅ Done | AlertsDashboard, alerts API. |
| 13 | Base vs Advanced view | ✅ Done | ViewToggle, CommanderView. |
| 14 | Collapsed sidebar = favicon only | ✅ Done | AppShell shows `/icon` when collapsed. |
| 15 | Browser tab title “Novartis Planner” | ✅ Done | layout.tsx metadata. |
| 16 | LAN access (optional) | — | Set NEXT_PUBLIC_CONGRESS_TWIN_API_URL and run backend with --host 0.0.0.0. |
| 17 | Teams bot (Phase 3) | ⏳ Not in scope | Optional future phase. |

---

## 5. File / Config Reference

- **Frontend entry**: `frontend/app/planner/page.tsx`, `frontend/app/layout.tsx` (title: Novartis Planner).
- **API client**: `frontend/lib/congressTwinApi.ts` (default base URL `http://localhost:8010`).
- **Backend entry**: `src/congress_twin/main.py`; planner routes: `src/congress_twin/api/v1/planner.py`.
- **Config**: `src/congress_twin/config/settings.py` (CORS, PG, Neo4j, Graph).
- **Migrations**: `migrations/001–005` (planner_tasks, plan_sync_state, start_date, external_events, agent_proposed_actions).
- **Docs**: `CONGRESS_TWIN_API_REFERENCE.md`, `PROJECT_LAYOUT.md`, `README.md`.

---

## 6. Running for Demo (LAN)

1. **Backend**: From `congress-twin/`:  
   `uv run uvicorn congress_twin.main:app --reload --port 8010`
2. **Frontend**: From `congress-twin/frontend/`:  
   `npm run dev`
3. **Open**: http://localhost:3000/planner (browser tab: **Novartis Planner**).

All assigned tasks listed above are covered except the optional Teams bot (Phase 3).
