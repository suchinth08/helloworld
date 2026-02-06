# Congress Twin

Separate project for the Congress Utility Bot / Digital Twin (Planner execution view + OR/agents/SSE). Lives in the same repo as the main Knowledge Graph Dashboard but is a **distinct project** with its own backend, config, and tests.

## Layout (NVS-GenAI aligned)

- **Backend:** `src/congress_twin/` — FastAPI app, config, api, services, agents, tools, lifecycle.
- **Frontend:** `frontend/` — Next.js app (Planner page, Dependency Lens, Attention Dashboard, Sync, etc.).
- **Tests:** `tests/` mirroring `src/congress_twin/` (TDD).

## Quick Setup (First Time)

**Load seed data** so the attention dashboard shows "Due next 7 days", "Critical path due next", and "Recently changed":

```bash
cd congress-twin
./setup.sh
```

Or manually:
```bash
uv sync
PYTHONPATH=src uv run python -m congress_twin.scripts.seed_congress_db
```

This creates `congress_twin.db` (SQLite) and loads 15 tasks with relative dates.

## Full stack run

From the **congress-twin** directory:

```bash
# Terminal 1 — Backend (port 8010)
cd congress-twin
PYTHONPATH=src uv run uvicorn congress_twin.main:app --reload --port 8010

# Terminal 2 — Frontend (port 3000)
cd congress-twin/frontend
npm install
npm run dev
```

Then open http://localhost:3000/planner

**Note:** `PYTHONPATH=src` is required so Python can find the `congress_twin` module in `src/`.

### Accept connections from other systems (LAN)

To allow other devices on your network (e.g. WiFi) to reach the API, run the backend bound to all interfaces:

```bash
cd congress-twin
PYTHONPATH=src uvicorn congress_twin.main:app --reload --port 8010 --host 0.0.0.0
```

Or with `uv` (include PYTHONPATH):

```bash
PYTHONPATH=src uv run uvicorn congress_twin.main:app --reload --port 8010 --host 0.0.0.0
```

Then other devices can call `http://<this-machine-ip>:8010` (e.g. `http://192.168.0.101:8010`). Set the frontend env `NEXT_PUBLIC_CONGRESS_TWIN_API_URL` to that URL when using from another machine.

## Run backend only

```bash
cd congress-twin
uv sync
PYTHONPATH=src uv run uvicorn congress_twin.main:app --reload --port 8010
```

## Run tests

```bash
cd congress-twin
uv sync
uv run pytest tests/ -v
```

## Environment

A `.env` file is provided (from `.env.example`). Uses **SQLite** (embedded database, no server required). Default database file: `congress_twin.db` in the project root. Set `SQLITE_DB_PATH` in `.env` to use a custom path.

**Note:** Graph operations (critical path, dependencies) use Python algorithms (NetworkX-compatible), no Neo4j required.

## Deploying to Another Environment

**Yes, it works automatically!** The app is fully self-contained with SQLite (no external dependencies).

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for complete deployment instructions, including:
- Setup steps for a new environment
- How to load seed data
- Troubleshooting
- Backup/restore

**Quick deploy:**
1. Copy `congress-twin/` directory to new machine
2. Run `./setup.sh` (or `uv sync` + seed script)
3. Start backend + frontend
4. Done! No Postgres/Neo4j needed.
