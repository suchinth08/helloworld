# Congress Twin — Project Layout (Separate Project Folder)

## Repo structure

```
accenture/
├── backend/                    # Existing Knowledge Graph Dashboard (unchanged)
├── frontend/                   # Existing; add Congress Twin route + view toggle
├── congress-twin/              # ★ Congress Twin (backend + frontend)
│   ├── README.md
│   ├── PROJECT_LAYOUT.md       # this file
│   ├── pyproject.toml          # uv, deps, ruff, pytest
│   ├── .env
│   ├── .env.example
│   ├── frontend/               # Next.js app — Congress Twin only (Planner UI)
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   ├── package.json
│   │   └── ...
│   ├── migrations/
│   ├── src/
│   │   └── congress_twin/      # Python package (absolute imports: congress_twin.*)
│   │       ├── __init__.py
│   │       ├── main.py         # FastAPI app, lifespan
│   │       ├── config/         # Pydantic BaseSettings
│   │       │   ├── __init__.py
│   │       │   └── settings.py
│   │       ├── api/
│   │       │   ├── __init__.py
│   │       │   └── v1/
│   │       │       ├── __init__.py
│   │       │       └── planner.py   # /api/v1/planner/*
│   │       ├── services/
│   │       │   ├── __init__.py
│   │       │   ├── planner_service.py
│   │       │   └── planner_simulated_data.py
│   │       ├── agents/         # Phase 2
│   │       │   ├── __init__.py
│   │       │   ├── ingestor_agent.py
│   │       │   ├── optimization_agent.py
│   │       │   ├── veeva_agent.py
│   │       │   └── monitor_agent.py
│   │       ├── tools/          # Phase 2 MCP
│   │       │   ├── __init__.py
│   │       │   └── mcp_server.py
│   │       └── lifecycle/
│   │           ├── __init__.py
│   │           └── startup.py  # init DB, clients
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_config.py
│   │   ├── services/
│   │   │   ├── test_planner_simulated_data.py
│   │   │   └── test_planner_service.py
│   │   └── api/
│   │       └── test_planner_api.py
│   └── scripts/
│       ├── seed_congress_db.py # Seed DB with Novartis Congress event data
│       └── simulate_congress.py
└── ...
```

## Integration

- **Backend:** Congress Twin runs as its own FastAPI app (port 8010) from `congress-twin/`.
- **Frontend:** Lives in `congress-twin/frontend/` (Next.js). Route `/planner` calls the backend at `http://localhost:8010/api/v1/planner/*`.
- **Data:** Congress Twin uses its own Postgres/Neo4j config (`.env`); planner tables in `public.planner_tasks`.

### Seeding Congress data

To load Novartis Congress event scheduling data into the DB (so the UI uses DB as source for the default plan):

- **CLI:** From `congress-twin/`: `uv run python -m congress_twin.scripts.seed_congress_db` (requires `CONGRESS_TWIN_PG_CONN` or default Postgres).
- **API:** `POST /api/v1/planner/seed` (optional `?plan_id=uc31-plan`). Ensures tables, upserts congress tasks, sets sync state.
- **Sync without Graph:** `POST /api/v1/planner/sync/uc31-plan` with Graph unconfigured also upserts congress seed data to DB.

After seeding (or after a sync with congress seed), the planner UI and all planner APIs read from the database for that plan. Task IDs are `task-001` … `task-015`; dependencies are defined in code (`get_simulated_dependencies`) and used for Dependency Lens and critical path.

**Attention dashboard (Due next 7 days, Critical path due next, Recently changed):** Seed and sync use relative dates for a subset of tasks (task-004–007), so after you run the seed (or sync without Graph), those cards will show data for the next 7 days. Re-run the seed or sync periodically to refresh the window.

## NVS-GenAI alignment

- **Absolute imports:** `from congress_twin.config.settings import get_settings`
- **Config:** Single `AppSettings` in `config/settings.py`
- **Lifespan:** Init in `lifecycle/startup.py`, used in `main.py`
- **Tests:** Mirror `src/congress_twin/` under `tests/`
