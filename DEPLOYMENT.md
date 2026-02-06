# Novartis Planner — Deployment Guide

This guide explains how to deploy and run Novartis Planner in a new environment. The app is **fully self-contained** with SQLite (no external database server required).

---

## ✅ Self-Contained & Portable

**Yes, it will work automatically in another environment without external dependencies!**

- ✅ **SQLite** — Embedded database (single file, no server)
- ✅ **Python dependencies** — All managed via `uv` (or pip)
- ✅ **No Postgres/Neo4j** — Removed, using SQLite + NetworkX
- ✅ **No external services** — Everything runs locally
- ✅ **Seed data** — Loaded via script or API

---

## Quick Start (New Environment)

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for frontend)
- **uv** (recommended) or **pip** (alternative)

### Step 1: Install uv (if not installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or use pip:
```bash
python3 -m pip install --upgrade pip
```

### Step 2: Clone/Copy the Project

```bash
# If using git
git clone <repo-url> congress-twin
cd congress-twin

# Or copy the entire congress-twin directory to the new machine
```

### Step 3: Setup Database & Load Seed Data

**Option A: Using the setup script (recommended)**

```bash
cd congress-twin
chmod +x setup.sh
./setup.sh
```

**Option B: Manual setup**

```bash
cd congress-twin

# Install dependencies
uv sync
# OR with pip: pip install -r requirements.txt (if you create one)

# Load seed data (creates SQLite DB and populates it)
PYTHONPATH=src uv run python -m congress_twin.scripts.seed_congress_db
```

**Option C: Via API (after starting backend)**

```bash
# Start backend first, then:
curl -X POST "http://localhost:8010/api/v1/planner/seed?plan_id=uc31-plan"
```

### Step 4: Start Backend

```bash
cd congress-twin
PYTHONPATH=src uv run uvicorn congress_twin.main:app --reload --port 8010
```

For LAN access (other devices on WiFi):
```bash
PYTHONPATH=src uv run uvicorn congress_twin.main:app --reload --port 8010 --host 0.0.0.0
```

### Step 5: Start Frontend

```bash
cd congress-twin/frontend
npm install
npm run dev
```

### Step 6: Open in Browser

- **Local:** http://localhost:3000/planner
- **LAN:** http://<your-ip>:3000/planner (if frontend is accessible)

---

## What Gets Created

After running the seed script:

1. **SQLite database:** `congress_twin.db` (in project root)
   - Contains: `planner_tasks`, `plan_sync_state`, `external_events`, `agent_proposed_actions`
   - **Portable:** Copy this file to backup/restore data

2. **Seed data loaded:**
   - 15 tasks (task-001 to task-015)
   - Relative dates set so **"Due next 7 days"**, **"Critical path due next"**, and **"Recently changed"** show data
   - Sync state initialized

---

## Environment Variables (Optional)

Create a `.env` file (copy from `.env.example`):

```bash
# SQLite database path (default: congress_twin.db in project root)
SQLITE_DB_PATH=congress_twin.db

# CORS origins (comma-separated)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_ALLOW_ALL=true

# Optional: MS Graph API (for live Planner sync)
# GRAPH_CLIENT_ID=...
# GRAPH_CLIENT_SECRET=...
# GRAPH_TENANT_ID=...
```

---

## Data Loading for Attention Dashboard

The seed script uses **relative dates** so the attention dashboard shows:

- **Due next 7 days:** task-004, task-005, task-006, task-007 (due in 2-6 days from now)
- **Critical path due next:** task-006, task-007 (on critical path, due soon)
- **Recently changed:** task-004, task-005, task-006, task-007 (modified in last few hours)

**To refresh dates** (if they're stale):
```bash
PYTHONPATH=src uv run python -m congress_twin.scripts.seed_congress_db
```

Or use the API:
```bash
curl -X POST "http://localhost:8010/api/v1/planner/seed?plan_id=uc31-plan"
```

---

## Deployment Checklist

- [ ] Python 3.11+ installed
- [ ] Node.js 18+ installed (for frontend)
- [ ] `uv` installed (or use pip)
- [ ] Project copied to new environment
- [ ] Dependencies installed (`uv sync`)
- [ ] Seed data loaded (creates SQLite DB)
- [ ] Backend started (port 8010)
- [ ] Frontend started (port 3000)
- [ ] Browser opens http://localhost:3000/planner
- [ ] Attention dashboard shows data (Due next 7 days, Critical path, Recently changed)

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'congress_twin'"
**Fix:** Always use `PYTHONPATH=src` when running:
```bash
PYTHONPATH=src uv run uvicorn congress_twin.main:app --reload --port 8010
```

### "Attention dashboard shows 0 items"
**Fix:** Run seed script to load data:
```bash
PYTHONPATH=src uv run python -m congress_twin.scripts.seed_congress_db
```

### "Database locked" (SQLite)
**Fix:** Only one process can write to SQLite at a time. Stop other instances.

### Frontend can't connect to backend
**Fix:** Check backend is running and CORS is configured. Frontend uses `http://localhost:8010` by default (or `NEXT_PUBLIC_CONGRESS_TWIN_API_URL` if set).

---

## Backup & Restore

**Backup:**
```bash
cp congress_twin.db congress_twin_backup_$(date +%Y%m%d).db
```

**Restore:**
```bash
cp congress_twin_backup_20250205.db congress_twin.db
```

---

## Production Deployment

For production, consider:

1. **Build frontend:** `cd frontend && npm run build && npm start` (or use a static host)
2. **Use a process manager:** PM2, systemd, or Docker
3. **Set environment variables:** `.env` file or environment
4. **Backup SQLite:** Regular backups of `congress_twin.db`
5. **HTTPS:** Use a reverse proxy (nginx, Caddy) for HTTPS

---

## Summary

✅ **Fully portable** — No external dependencies  
✅ **Self-contained** — SQLite embedded database  
✅ **Easy setup** — Run `setup.sh` or seed script  
✅ **Works anywhere** — Python + Node.js is all you need
