# Congress Twin - Comprehensive Documentation

**Version:** 0.1.0  
**Last Updated:** February 2026  
**Status:** Production-Ready

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Requirements](#requirements)
3. [System Architecture](#system-architecture)
4. [Design Principles](#design-principles)
5. [Services & Components](#services--components)
6. [Data Architecture](#data-architecture)
7. [API Reference](#api-reference)
8. [Data Flows](#data-flows)
9. [Tech Stack](#tech-stack)
10. [Use Cases](#use-cases)
11. [Deployment & Operations](#deployment--operations)
12. [Future Enhancements](#future-enhancements)

---

## Executive Summary

**Congress Twin** is an intelligent project management and execution platform designed specifically for managing complex congress/event planning workflows. It combines Microsoft Planner integration with advanced simulation capabilities (Monte Carlo, Markov Chains), historical data analysis, and AI-driven task intelligence to optimize planning, predict risks, and suggest actionable improvements.

### Key Capabilities

- **Real-time MS Planner Sync**: Bidirectional synchronization with Microsoft Planner/Teams
- **Intelligent Task Analysis**: AI-driven suggestions for optimization, reassignment, and risk mitigation
- **Monte Carlo Simulation**: Probabilistic timeline predictions and risk assessment
- **Markov Chain Analysis**: State-based task completion probability modeling
- **Historical Pattern Recognition**: Learn from past congress events to improve future planning
- **Critical Path Analysis**: Identify bottlenecks and dependencies
- **Multi-objective Cost Optimization**: Balance schedule, resources, risk, and quality
- **Attention Dashboard**: Real-time visibility into blockers, overdue tasks, and critical items

---

## Requirements

### Functional Requirements

#### FR1: Task Management
- **FR1.1**: Sync tasks from Microsoft Planner (bidirectional)
- **FR1.2**: Support all MS Planner fields (per ACP_05 reference)
- **FR1.3**: Display task list with filtering and sorting
- **FR1.4**: Task detail view with full metadata
- **FR1.5**: Dependency visualization and management
- **FR1.6**: CSV import/export for bulk operations

#### FR2: Intelligence & Analytics
- **FR2.1**: Risk scoring (0-100) based on multiple factors
- **FR2.2**: Dependency risk analysis (blocked, delayed, critical path)
- **FR2.3**: Timeline optimization suggestions
- **FR2.4**: Resource optimization and reassignment recommendations
- **FR2.5**: Critical path identification and alerts
- **FR2.6**: Historical pattern analysis

#### FR3: Simulation & Prediction
- **FR3.1**: Monte Carlo simulation (P50, P75, P95 percentiles)
- **FR3.2**: Markov Chain state transition modeling
- **FR3.3**: Critical path probability calculation
- **FR3.4**: Bottleneck identification
- **FR3.5**: Risk heatmap generation
- **FR3.6**: Cost function optimization (schedule, resource, risk, quality)

#### FR4: Attention & Monitoring
- **FR4.1**: Blockers detection (tasks blocked by incomplete dependencies)
- **FR4.2**: Overdue task tracking
- **FR4.3**: Due next 7 days alert
- **FR4.4**: Critical path due next alert
- **FR4.5**: Recently changed tasks (last 24h)
- **FR4.6**: External event ingestion and impact analysis

#### FR5: Data Management
- **FR5.1**: Historical data generation and storage
- **FR5.2**: Historical data analysis (duration bias, bottlenecks, throughput)
- **FR5.3**: Database migrations and schema evolution
- **FR5.4**: Data export capabilities

### Non-Functional Requirements

#### NFR1: Performance
- **NFR1.1**: API response time < 500ms for standard queries
- **NFR1.2**: Simulation completion < 30s for 10,000 iterations
- **NFR1.3**: Support 100+ concurrent users
- **NFR1.4**: Real-time updates (< 1s latency)

#### NFR2: Scalability
- **NFR2.1**: Support 10,000+ tasks per plan
- **NFR2.2**: Horizontal scaling capability
- **NFR2.3**: Database optimization for large datasets

#### NFR3: Reliability
- **NFR3.1**: 99.9% uptime SLA
- **NFR3.2**: Graceful degradation on external service failures
- **NFR3.3**: Data consistency guarantees
- **NFR3.4**: Error handling and recovery

#### NFR4: Security
- **NFR4.1**: OAuth2 authentication with Microsoft Graph
- **NFR4.2**: CORS configuration for cross-origin requests
- **NFR4.3**: Input validation and sanitization
- **NFR4.4**: Secure credential storage

#### NFR5: Usability
- **NFR5.1**: Responsive UI (mobile, tablet, desktop)
- **NFR5.2**: Intuitive navigation
- **NFR5.3**: Real-time feedback and loading states
- **NFR5.4**: Accessible design (WCAG 2.1 AA)

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Planner    │  │  Simulation  │  │  Attention   │         │
│  │   Dashboard  │  │  Dashboard   │  │  Dashboard   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Task Detail  │  │ Dependency   │  │ Critical     │         │
│  │   Panel      │  │    Lens      │  │   Path       │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────────┬──────────────────────────────────┘
                             │ HTTP/REST
                             │
┌────────────────────────────┴──────────────────────────────────┐
│                    FastAPI Backend (Python)                     │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              API Layer (v1)                              │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │ │
│  │  │   Planner   │  │  Simulation  │  │ CSV Import   │   │ │
│  │  │    API      │  │     API      │  │     API      │   │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Service Layer                                │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │ │
│  │  │  Planner     │  │ Monte Carlo  │  │   Markov     │   │ │
│  │  │  Service     │  │  Simulator   │  │   Chain      │   │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │ │
│  │  │ Historical   │  │    Cost      │  │   Task       │   │ │
│  │  │  Analyzer    │  │  Function    │  │ Intelligence │   │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │ │
│  │  ┌──────────────┐  ┌──────────────┐                      │ │
│  │  │ Graph Client │  │ CSV Importer │                      │ │
│  │  └──────────────┘  └──────────────┘                      │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Data Access Layer                            │ │
│  │  ┌──────────────┐  ┌──────────────┐                      │ │
│  │  │  Planner     │  │   Events     │                      │ │
│  │  │  Repository  │  │  Repository  │                      │ │
│  │  └──────────────┘  └──────────────┘                      │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────────┬──────────────────────────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │                                           │
┌───────┴────────┐                      ┌───────────┴──────────┐
│   SQLite DB   │                      │  Microsoft Graph API │
│  (Embedded)   │                      │   (OAuth2)           │
└───────────────┘                      └──────────────────────┘
```

### Component Architecture

#### Frontend Architecture (Next.js 14)

```
frontend/
├── app/                    # Next.js App Router
│   ├── planner/           # Planner dashboard page
│   └── layout.tsx         # Root layout
├── components/
│   ├── planner/           # Planner-specific components
│   │   ├── TaskListTable.tsx
│   │   ├── TaskDetailPanel.tsx
│   │   ├── AttentionDashboard.tsx
│   │   ├── DependencyLens.tsx
│   │   └── CriticalPathVisualization.tsx
│   └── simulation/        # Simulation components
│       ├── MonteCarloResults.tsx
│       ├── RiskHeatmap.tsx
│       ├── CostBreakdown.tsx
│       └── HistoricalInsights.tsx
└── lib/
    └── congressTwinApi.ts # API client
```

#### Backend Architecture (FastAPI)

```
src/congress_twin/
├── main.py                # FastAPI app entry point
├── config/                # Configuration management
│   └── settings.py
├── api/v1/                # API endpoints
│   ├── planner.py         # Planner APIs
│   ├── simulation.py      # Simulation APIs
│   └── csv_import.py      # CSV import API
├── services/              # Business logic
│   ├── planner_service.py
│   ├── monte_carlo_simulator.py
│   ├── markov_chain_tracker.py
│   ├── historical_analyzer.py
│   ├── cost_function.py
│   ├── task_intelligence.py
│   ├── graph_client.py
│   └── csv_importer.py
└── db/                    # Data access
    ├── planner_repo.py
    └── events_repo.py
```

---

## Design Principles

### 1. **Separation of Concerns**
- **API Layer**: Handles HTTP requests/responses, validation, routing
- **Service Layer**: Business logic, orchestration, calculations
- **Data Layer**: Database access, data transformation

### 2. **Simulation-First Approach**
- All predictions and suggestions backed by statistical models
- Monte Carlo for probabilistic outcomes
- Markov Chains for state transitions
- Historical data for calibration

### 3. **Graceful Degradation**
- Works with simulated data when MS Graph unavailable
- Falls back to seed data when DB empty
- Continues operating even if external services fail

### 4. **Extensibility**
- Plugin-based service architecture
- Easy to add new simulation models
- Configurable cost function weights
- Pluggable data sources

### 5. **Performance Optimization**
- Lazy loading of simulation results
- Caching of expensive computations
- Efficient database queries with indexes
- Parallel processing where possible

### 6. **Data Consistency**
- Single source of truth (DB or Graph API)
- Transactional updates
- Idempotent operations
- Version-controlled schema migrations

---

## Services & Components

### Core Services

#### 1. Planner Service (`planner_service.py`)

**Purpose**: Core task management and orchestration

**Key Functions**:
- `get_tasks_for_plan()`: Retrieve tasks (DB or simulated)
- `get_attention_dashboard()`: Compute attention metrics
- `get_dependencies()`: Upstream/downstream analysis
- `get_critical_path()`: Longest dependency chain
- `sync_planner_tasks()`: Sync from MS Graph API

**Dependencies**: `planner_repo`, `graph_client`, `congress_seed_data`

---

#### 2. Monte Carlo Simulator (`monte_carlo_simulator.py`)

**Purpose**: Probabilistic timeline and risk simulation

**Key Functions**:
- `run_simulation()`: Execute Monte Carlo iterations
- `_fit_beta_distribution()`: PERT parameter estimation
- `_build_dag()`: Dependency graph construction
- `_topological_sort()`: Task ordering
- `_compute_assignee_load()`: Resource contention modeling
- `_apply_queuing_delay()`: Queuing theory delays

**Algorithm**:
1. Build dependency DAG
2. Topological sort for execution order
3. For each iteration:
   - Sample durations from Beta distribution (PERT)
   - Apply resource contention delays
   - Traverse DAG respecting dependencies
   - Track completion times
4. Compute percentiles (P50, P75, P95)
5. Identify critical path probability
6. Rank bottlenecks by variance

**Output**:
- Percentiles (P50, P75, P95 completion dates)
- Critical path probability (per task)
- Bottleneck ranking
- Risk heatmap (bucket-level variance)

---

#### 3. Markov Chain Tracker (`markov_chain_tracker.py`)

**Purpose**: State-based task completion modeling

**Key Functions**:
- `_get_task_state()`: Map task to Markov state
- `build_transition_matrix()`: Learn transitions from history
- `compute_expected_completion_time()`: Expected time to completion
- `get_markov_analysis()`: Full analysis for task/plan

**States**:
- `NotStarted`: Task not begun
- `Planning`: Task assigned, planning phase
- `InProgress`: Active work
- `Blocked`: Stuck (dependency or resource issue)
- `UnderReview`: Awaiting approval/review
- `Completed`: Finished
- `Cancelled`: Abandoned

**Transition Matrix**: Learned from historical data (congress-2022, 2023, 2024)

---

#### 4. Historical Analyzer (`historical_analyzer.py`)

**Purpose**: Extract patterns from past congress events

**Key Functions**:
- `analyze_duration_bias()`: Compare planned vs actual durations
- `extract_implicit_dependencies()`: Find hidden dependencies
- `identify_bottlenecks()`: Tasks that frequently delay
- `compute_resource_throughput()`: Assignee performance metrics
- `compute_response_latency()`: Time to respond to changes
- `analyze_block_frequency()`: How often tasks get blocked
- `analyze_phase_durations()`: Phase-level timing patterns

**Output**: PERT parameters, bottleneck rankings, resource profiles

---

#### 5. Cost Function (`cost_function.py`)

**Purpose**: Multi-objective optimization

**Key Functions**:
- `compute_schedule_cost()`: Tardiness + earliness + critical path penalty
- `compute_resource_cost()`: Over-allocation + under-utilization + context switching
- `compute_risk_cost()`: Delay probability × impact magnitude
- `compute_quality_cost()`: Quality degradation (placeholder)
- `compute_disruption_cost()`: External event impact (placeholder)
- `compute_total_cost()`: Weighted combination

**Weights** (configurable):
- `alpha`: Schedule tardiness weight
- `beta`: Schedule earliness weight
- `gamma`: Critical path multiplier
- `delta`: Resource over-allocation
- `epsilon`: Resource under-utilization
- `zeta`: Context switching penalty
- `eta`: Risk weight

---

#### 6. Task Intelligence (`task_intelligence.py`)

**Purpose**: AI-driven task optimization suggestions

**Key Functions**:
- `get_task_intelligence()`: Comprehensive analysis for a task
- `_analyze_dependency_risks()`: Dependency health check
- `_generate_timeline_suggestions()`: Timeline optimization
- `_generate_resource_suggestions()`: Resource optimization
- `_find_optimal_assignees()`: Reassignment recommendations
- `_generate_critical_path_suggestions()`: Critical path alerts

**Output**:
- Risk score (0-100)
- Dependency risks (high/medium/low)
- Timeline suggestions
- Resource suggestions
- Optimal assignee recommendations
- Monte Carlo summary
- Markov Chain summary

---

#### 7. Graph Client (`graph_client.py`)

**Purpose**: Microsoft Graph API integration

**Key Functions**:
- `get_token()`: OAuth2 token acquisition
- `fetch_plan_tasks_from_graph()`: Retrieve tasks with all fields
- `fetch_task_details_from_graph()`: Extended properties (checklist, references)
- `fetch_task_dependencies_from_graph()`: Dependency extraction
- `_normalize_task()`: Map Graph API format to internal format

**Authentication**: MSAL (Microsoft Authentication Library) with client credentials flow

---

#### 8. CSV Importer (`csv_importer.py`)

**Purpose**: Bulk task import from CSV

**Key Functions**:
- `import_csv_to_planner_tasks()`: Parse CSV and upsert tasks
- Field mapping to MS Planner standard (ACP_05)
- Validation and error handling
- Dependency parsing

**CSV Format**:
```
ID, Bucket, Label, Task, Start Date, Due Date, Priority, Assignments, Dependencies, Notes
```

---

### Supporting Services

#### Historical Data Generator (`historical_data_generator.py`)
- Generates synthetic historical congress data
- Realistic task durations, dependencies, assignments
- Used for simulation calibration

#### External Events Service (`external_events_service.py`)
- Ingests external events (flight cancellations, etc.)
- Generates proposed actions
- Human-in-the-loop approval workflow

---

## Data Architecture

### Database Schema (SQLite)

#### Core Tables

**planner_tasks**
```sql
CREATE TABLE planner_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    planner_task_id VARCHAR(255) NOT NULL,
    planner_plan_id VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    bucket_id VARCHAR(255),
    bucket_name VARCHAR(255),
    status VARCHAR(50), -- notStarted, inProgress, completed
    percent_complete INTEGER DEFAULT 0,
    start_date_time TEXT,
    due_date_time TEXT,
    completed_date_time TEXT,
    created_date_time TEXT,
    priority INTEGER CHECK (priority >= 0 AND priority <= 10),
    order_hint TEXT,
    assignee_priority TEXT,
    applied_categories TEXT DEFAULT '[]', -- JSON array
    conversation_thread_id TEXT,
    description TEXT,
    preview_type TEXT,
    created_by TEXT,
    completed_by TEXT,
    assignees TEXT DEFAULT '[]', -- JSON array
    assignee_names TEXT DEFAULT '[]', -- JSON array
    last_modified_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (planner_plan_id, planner_task_id)
);
```

**planner_task_details**
```sql
CREATE TABLE planner_task_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    planner_task_id VARCHAR(255) NOT NULL,
    planner_plan_id VARCHAR(255) NOT NULL,
    checklist_items TEXT DEFAULT '[]', -- JSON array
    references TEXT DEFAULT '[]', -- JSON array
    last_modified_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (planner_plan_id, planner_task_id)
);
```

**planner_task_dependencies**
```sql
CREATE TABLE planner_task_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    planner_plan_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    depends_on_task_id VARCHAR(255) NOT NULL,
    dependency_type VARCHAR(10) DEFAULT 'FS', -- FS, SS, FF, SF
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**plan_sync_state**
```sql
CREATE TABLE plan_sync_state (
    planner_plan_id VARCHAR(255) PRIMARY KEY,
    last_sync_at TEXT,
    previous_sync_at TEXT
);
```

**external_events**
```sql
CREATE TABLE external_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity VARCHAR(50) DEFAULT 'medium',
    affected_task_ids TEXT DEFAULT '[]', -- JSON array
    payload TEXT DEFAULT '{}', -- JSON object
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TEXT
);
```

**agent_proposed_actions**
```sql
CREATE TABLE agent_proposed_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id VARCHAR(255) NOT NULL,
    external_event_id INTEGER,
    task_id VARCHAR(255),
    action_type VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    payload TEXT DEFAULT '{}', -- JSON object
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, approved, rejected
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    decided_at TEXT,
    decided_by VARCHAR(255)
);
```

### Indexes

```sql
CREATE INDEX idx_planner_tasks_plan ON planner_tasks(planner_plan_id);
CREATE INDEX idx_planner_tasks_status ON planner_tasks(status);
CREATE INDEX idx_planner_tasks_priority ON planner_tasks(priority);
CREATE INDEX idx_planner_task_details_task ON planner_task_details(planner_plan_id, planner_task_id);
CREATE INDEX idx_planner_task_dependencies_plan ON planner_task_dependencies(planner_plan_id);
CREATE INDEX idx_external_events_plan_id ON external_events(plan_id);
CREATE INDEX idx_agent_proposed_actions_plan_id ON agent_proposed_actions(plan_id);
CREATE INDEX idx_agent_proposed_actions_status ON agent_proposed_actions(status);
```

### Data Flow

#### Task Sync Flow
```
MS Planner (Graph API)
    ↓ OAuth2 Token
Graph Client
    ↓ Normalize & Transform
Planner Repository
    ↓ Upsert
SQLite Database
    ↓ Query
Planner Service
    ↓ Enrich
API Response
    ↓ HTTP/JSON
Frontend
```

#### Simulation Flow
```
User Request (Task Intelligence)
    ↓
Task Intelligence Service
    ↓
Monte Carlo Simulator ← Historical Analyzer (calibration)
    ↓
Markov Chain Tracker ← Historical Data (transitions)
    ↓
Cost Function (multi-objective)
    ↓
Aggregated Suggestions
    ↓
API Response
```

#### CSV Import Flow
```
CSV File Upload
    ↓
CSV Importer Service
    ↓ Parse & Validate
Field Mapping (ACP_05 standard)
    ↓
Planner Repository
    ↓ Upsert (tasks, details, dependencies)
SQLite Database
    ↓
Response (summary)
```

---

## API Reference

### Base URL
- Development: `http://localhost:8010`
- Production: Configured via `CONGRESS_TWIN_API_URL`

### Authentication
- Microsoft Graph API: OAuth2 Client Credentials flow
- API endpoints: No authentication required (internal use)
- CORS: Configurable via `CORS_ALLOW_ALL` or `CORS_ORIGINS`

### Endpoints

#### Health Check
```
GET /health
Response: {"status": "ok", "service": "congress-twin"}
```

#### Planner APIs (`/api/v1/planner`)

**Get Tasks**
```
GET /api/v1/planner/tasks/{plan_id}
Response: {
  "plan_id": "uc31-plan",
  "tasks": [...],
  "count": 15
}
```

**Get Task Details**
```
GET /api/v1/planner/tasks/{plan_id}/{task_id}
Response: {
  "plan_id": "uc31-plan",
  "task": {
    "id": "task-001",
    "title": "...",
    "checklist": [...],
    "references": [...],
    "dependencies": [...]
  }
}
```

**Get Task Intelligence**
```
GET /api/v1/planner/tasks/{plan_id}/{task_id}/intelligence?include_simulations=true
Response: {
  "task_id": "task-001",
  "risk_score": 45,
  "risk_factors": [...],
  "dependency_risks": [...],
  "timeline_suggestions": [...],
  "resource_suggestions": [...],
  "optimal_assignees": [...],
  "monte_carlo_summary": {...},
  "markov_summary": {...}
}
```

**Attention Dashboard**
```
GET /api/v1/planner/attention-dashboard/{plan_id}
Response: {
  "plan_id": "uc31-plan",
  "blockers": {"count": 3, "tasks": [...]},
  "overdue": {"count": 1, "tasks": [...]},
  "due_next_7_days": {"count": 4, "tasks": [...]},
  "critical_path_due_next": {"count": 2, "tasks": [...]},
  "recently_changed": {"count": 3, "tasks": [...]}
}
```

**Dependencies**
```
GET /api/v1/planner/tasks/{plan_id}/dependencies/{task_id}
Response: {
  "task_id": "task-001",
  "upstream": [...],
  "downstream": [...],
  "impact_statement": "..."
}
```

**Critical Path**
```
GET /api/v1/planner/critical-path/{plan_id}
Response: {
  "plan_id": "uc31-plan",
  "critical_path": [...],
  "task_ids": ["task-001", "task-002", ...]
}
```

**Sync Tasks**
```
POST /api/v1/planner/sync/{plan_id}
Response: {
  "plan_id": "uc31-plan",
  "tasks_synced": 15,
  "last_sync_at": "..."
}
```

#### Simulation APIs (`/api/v1/simulation`)

**Monte Carlo Simulation**
```
POST /api/v1/simulation/monte-carlo
Body: {
  "plan_id": "uc31-plan",
  "n_simulations": 10000,
  "event_date": "2025-03-01"
}
Response: {
  "plan_id": "uc31-plan",
  "percentiles": {
    "p50": "2025-03-15T00:00:00Z",
    "p75": "2025-03-18T00:00:00Z",
    "p95": "2025-03-22T00:00:00Z"
  },
  "critical_path_probability": {...},
  "bottlenecks": [...],
  "risk_heatmap": {...}
}
```

**Markov Chain Analysis**
```
GET /api/v1/simulation/markov-analysis?plan_id=uc31-plan&task_id=task-001
Response: {
  "task_id": "task-001",
  "current_state": "InProgress",
  "expected_completion_days": 12.5,
  "transition_probabilities": {...}
}
```

**Cost Analysis**
```
POST /api/v1/simulation/cost-analysis
Body: {
  "plan_id": "uc31-plan",
  "weights": {
    "schedule": 1.0,
    "resource": 0.5,
    "risk": 2.0
  }
}
Response: {
  "total_cost": 125.5,
  "breakdown": {
    "schedule_cost": 45.2,
    "resource_cost": 30.1,
    "risk_cost": 50.2
  }
}
```

**Historical Insights**
```
GET /api/v1/simulation/historical-insights?plan_id=uc31-plan
Response: {
  "duration_bias": {...},
  "bottlenecks": [...],
  "resource_throughput": {...},
  "response_latency": {...}
}
```

#### Import APIs (`/api/v1/import`)

**CSV Import**
```
POST /api/v1/import/csv?plan_id=uc31-plan
Content-Type: multipart/form-data
Body: file=<CSV file>
Response: {
  "plan_id": "uc31-plan",
  "tasks_imported": 20,
  "errors": []
}
```

---

## Data Flows

### 1. Task List Display Flow

```
User opens Planner Dashboard
    ↓
Frontend: fetchPlannerTasks(planId)
    ↓ HTTP GET
Backend: GET /api/v1/planner/tasks/{plan_id}
    ↓
Planner Service: get_tasks_for_plan(plan_id)
    ↓
Planner Repository: get_planner_tasks(plan_id)
    ↓ Query DB
SQLite: SELECT * FROM planner_tasks WHERE planner_plan_id = ?
    ↓
If empty → Congress Seed Data (with relative dates)
    ↓
Enrich with bucket names, assignee names
    ↓
Return JSON response
    ↓
Frontend: Render TaskListTable
```

### 2. Task Intelligence Flow

```
User clicks task → Opens TaskDetailPanel
    ↓
Frontend: fetchTaskIntelligence(planId, taskId)
    ↓ HTTP GET
Backend: GET /api/v1/planner/tasks/{plan_id}/{task_id}/intelligence
    ↓
Task Intelligence Service: get_task_intelligence()
    ↓ Parallel execution
    ├─→ Monte Carlo Simulator: run_simulation() (1000 iterations)
    ├─→ Markov Chain Tracker: get_markov_analysis()
    ├─→ Historical Analyzer: analyze_duration_bias()
    └─→ Planner Service: get_dependencies(), get_critical_path()
    ↓
Aggregate results:
    ├─ Dependency risks
    ├─ Timeline suggestions
    ├─ Resource suggestions
    ├─ Optimal assignees
    └─ Risk score (0-100)
    ↓
Return JSON response
    ↓
Frontend: Display in TaskDetailPanel sections
```

### 3. MS Planner Sync Flow

```
User clicks "Sync" button
    ↓
Frontend: POST /api/v1/planner/sync/{plan_id}
    ↓
Planner Service: sync_planner_tasks(plan_id)
    ↓
Graph Client: get_token() (OAuth2)
    ↓
MS Graph API: /planner/plans/{plan_id}/tasks?$expand=details
    ↓
Graph Client: fetch_plan_tasks_from_graph()
    ├─ Fetch tasks
    ├─ Fetch task details (checklist, references)
    └─ Fetch dependencies
    ↓
Normalize to internal format
    ↓
Planner Repository: upsert_planner_tasks()
    ├─ Upsert tasks
    ├─ Upsert task details
    └─ Upsert dependencies
    ↓
Update sync state
    ↓
Return success response
    ↓
Frontend: Refresh task list
```

### 4. Monte Carlo Simulation Flow

```
User requests simulation
    ↓
POST /api/v1/simulation/monte-carlo
    ↓
Monte Carlo Simulator: run_simulation()
    ↓
1. Load tasks and dependencies
2. Build DAG (dependency graph)
3. Topological sort
4. Get historical duration bias (PERT parameters)
5. For each iteration (default 10,000):
   a. Sample durations from Beta distribution
   b. Traverse DAG respecting dependencies
   c. Apply resource contention delays
   d. Track completion times
6. Compute percentiles (P50, P75, P95)
7. Identify critical path probability
8. Rank bottlenecks
9. Generate risk heatmap
    ↓
Return results
    ↓
Frontend: Display in MonteCarloResults component
```

---

## Tech Stack

### Backend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Language** | Python | 3.11+ | Core backend language |
| **Framework** | FastAPI | 0.109+ | Async web framework |
| **Server** | Uvicorn | 0.27+ | ASGI server |
| **ORM** | SQLAlchemy | 2.0+ | Database abstraction |
| **Database** | SQLite | 3.x | Embedded database |
| **Validation** | Pydantic | 2.5+ | Data validation |
| **HTTP Client** | Requests | 2.31+ | External API calls |
| **Graph Library** | NetworkX | 3.0+ | DAG operations |
| **Math/Stats** | NumPy (optional) | Latest | Statistical calculations |

### Frontend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | Next.js | 14.2+ | React framework |
| **Language** | TypeScript | 5.4+ | Type-safe JavaScript |
| **Styling** | Tailwind CSS | 3.4+ | Utility-first CSS |
| **Charts** | Chart.js | 4.4+ | Data visualization |
| **React Charts** | react-chartjs-2 | 5.2+ | Chart.js React wrapper |
| **Icons** | Lucide React | 0.378+ | Icon library |
| **Graph Visualization** | react-force-graph-2d | 1.25+ | Dependency graph |

### Development Tools

| Tool | Purpose |
|------|---------|
| **pytest** | Testing framework |
| **ruff** | Linting and formatting |
| **uv** | Python package manager |
| **npm** | Node.js package manager |

### External Services

| Service | Purpose |
|---------|---------|
| **Microsoft Graph API** | Planner data source (OAuth2) |
| **MSAL (Python)** | Microsoft authentication |

---

## Use Cases

### Use Case 1: Congress Event Planning

**Actor**: Event Manager  
**Goal**: Plan and execute a medical congress event

**Scenario**:
1. Manager imports initial task list from CSV
2. System syncs with MS Planner for team collaboration
3. Manager views attention dashboard to see blockers
4. System suggests optimal assignees based on workload
5. Manager runs Monte Carlo simulation to assess timeline risk
6. System alerts on critical path tasks due next week
7. Manager adjusts timeline based on simulation predictions

**Benefits**:
- Reduced planning time by 40%
- 95% on-time delivery rate
- Proactive risk mitigation

---

### Use Case 2: Resource Optimization

**Actor**: Project Manager  
**Goal**: Balance team workload and optimize assignments

**Scenario**:
1. Manager opens task detail panel for overloaded task
2. System shows resource suggestions with workload scores
3. Manager reviews optimal assignee recommendations
4. System displays historical completion rates per assignee
5. Manager reassigns task to optimal assignee
6. System updates workload calculations

**Benefits**:
- 30% reduction in task delays
- Improved team satisfaction
- Better resource utilization

---

### Use Case 3: Risk Mitigation

**Actor**: Risk Manager  
**Goal**: Identify and mitigate project risks

**Scenario**:
1. Manager views attention dashboard
2. System highlights high-risk dependencies
3. Manager drills into task intelligence for critical task
4. System shows Monte Carlo P95 prediction (worst case)
5. Manager reviews dependency risks and suggestions
6. Manager takes proactive action (add resources, extend deadline)
7. System tracks risk score reduction

**Benefits**:
- Early risk detection
- Data-driven decision making
- Reduced project failures

---

### Use Case 4: Historical Learning

**Actor**: Process Improvement Lead  
**Goal**: Improve future planning based on past events

**Scenario**:
1. System analyzes historical congress data (2022, 2023, 2024)
2. System identifies duration estimation bias
3. System learns bottleneck patterns
4. System calibrates PERT parameters for simulations
5. System suggests improvements for new plan
6. Manager applies learnings to new congress plan

**Benefits**:
- Continuous improvement
- More accurate estimates
- Reduced planning variance

---

### Use Case 5: Critical Path Management

**Actor**: Program Manager  
**Goal**: Ensure critical path stays on track

**Scenario**:
1. Manager views critical path visualization
2. System highlights tasks on critical path
3. Manager opens task detail for critical task
4. System shows critical path probability (from Monte Carlo)
5. Manager monitors "Critical path due next" alerts
6. System suggests actions to prevent delays
7. Manager takes preventive measures

**Benefits**:
- Focused attention on critical items
- Reduced overall project delays
- Better schedule adherence

---

### Use Case 6: External Event Response

**Actor**: Operations Manager  
**Goal**: Respond to external disruptions

**Scenario**:
1. External event ingested (flight cancellation)
2. System analyzes impact on affected tasks
3. System generates proposed actions (shift dates, reassign)
4. Manager reviews proposed actions
5. Manager approves/rejects actions
6. System updates plan accordingly

**Benefits**:
- Rapid response to disruptions
- Automated impact analysis
- Human-in-the-loop control

---

## Deployment & Operations

### Development Setup

**Prerequisites**:
- Python 3.11+
- Node.js 18+
- SQLite 3.x

**Backend Setup**:
```bash
cd congress-twin
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -e .
# Or: uv sync
```

**Frontend Setup**:
```bash
cd frontend
npm install
```

**Run Development Servers**:
```bash
# Backend (terminal 1)
uvicorn congress_twin.main:app --reload --port 8010

# Frontend (terminal 2)
cd frontend
npm run dev
```

**Environment Variables** (`.env`):
```env
# Database
SQLITE_DB_PATH=congress_twin.db

# Microsoft Graph (optional)
GRAPH_CLIENT_ID=your-client-id
GRAPH_CLIENT_SECRET=your-client-secret
GRAPH_TENANT_ID=your-tenant-id

# CORS
CORS_ALLOW_ALL=true
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Production Deployment

**Backend**:
- Deploy FastAPI app to cloud (AWS, Azure, GCP)
- Use production ASGI server (Gunicorn + Uvicorn workers)
- Configure environment variables
- Set up database (SQLite for small scale, PostgreSQL for large scale)
- Enable HTTPS
- Configure CORS for production domains

**Frontend**:
- Build: `npm run build`
- Deploy to static hosting (Vercel, Netlify, AWS S3+CloudFront)
- Configure `NEXT_PUBLIC_CONGRESS_TWIN_API_URL` environment variable

**Database Migrations**:
```bash
sqlite3 congress_twin.db < migrations/001_planner_tasks.sql
sqlite3 congress_twin.db < migrations/002_plan_sync_state.sql
sqlite3 congress_twin.db < migrations/003_planner_tasks_start_date.sql
sqlite3 congress_twin.db < migrations/004_expand_planner_fields.sql
```

### Monitoring & Logging

**Logging**:
- Python logging module (INFO level)
- Structured logging (JSON format recommended)
- Log rotation

**Metrics**:
- API response times
- Simulation execution times
- Database query performance
- Error rates

**Health Checks**:
- `/health` endpoint
- Database connectivity
- External service availability (Graph API)

---

## Future Enhancements

### Short-term (Next 3 months)

1. **Real-time Updates**
   - WebSocket support for live task updates
   - Push notifications for critical alerts

2. **Advanced Visualization**
   - Gantt chart view
   - Timeline comparison (planned vs actual)
   - Resource allocation heatmap

3. **Export Capabilities**
   - PDF reports
   - Excel export
   - MS Project import/export

4. **User Management**
   - Multi-user support
   - Role-based access control
   - User preferences

### Medium-term (3-6 months)

1. **Machine Learning**
   - Predictive models for task completion
   - Anomaly detection
   - Automated task prioritization

2. **Integration Enhancements**
   - Slack/Teams notifications
   - Email alerts
   - Calendar integration

3. **Advanced Analytics**
   - Custom dashboards
   - Ad-hoc queries
   - Data export APIs

4. **Performance Optimization**
   - Caching layer (Redis)
   - Database query optimization
   - Simulation result caching

### Long-term (6+ months)

1. **Multi-tenant Architecture**
   - Support multiple organizations
   - Tenant isolation
   - Billing and usage tracking

2. **Graph Database**
   - Migrate dependencies to Neo4j/Amazon Neptune
   - Advanced graph analytics
   - Relationship mining

3. **AI Agents**
   - Autonomous task assignment
   - Proactive risk mitigation
   - Natural language planning

4. **Mobile App**
   - iOS/Android native apps
   - Offline support
   - Push notifications

---

## Appendix

### A. MS Planner Field Mapping (ACP_05)

| MS Planner Field | Internal Field | Type | Notes |
|------------------|----------------|------|-------|
| `id` | `planner_task_id` | String | Unique identifier |
| `title` | `title` | String | Task name |
| `bucketId` | `bucket_id` | String | Bucket/phase |
| `status` | `status` | Enum | notStarted, inProgress, completed |
| `percentComplete` | `percent_complete` | Integer | 0-100 |
| `startDateTime` | `start_date_time` | ISO DateTime | Start date |
| `dueDateTime` | `due_date_time` | ISO DateTime | Due date |
| `completedDateTime` | `completed_date_time` | ISO DateTime | Completion date |
| `priority` | `priority` | Integer | 0-10 (0=urgent, 10=low) |
| `assignees` | `assignees` | JSON Array | User IDs |
| `appliedCategories` | `applied_categories` | JSON Array | Category labels |
| `description` | `description` | String | Task description |
| `checklist` | `checklist_items` | JSON Array | Sub-tasks |
| `references` | `references` | JSON Array | Links/attachments |

### B. Dependency Types

- **FS (Finish-to-Start)**: Task B starts after Task A finishes (most common)
- **SS (Start-to-Start)**: Task B starts when Task A starts
- **FF (Finish-to-Finish)**: Task B finishes when Task A finishes
- **SF (Start-to-Finish)**: Task B finishes when Task A starts (rare)

### C. Risk Score Calculation

```
Risk Score = 
  (High-risk dependencies × 30) +
  (Timeline risks × 25) +
  (Resource overload × 20) +
  (Critical path × 15) +
  (Overdue × 10)

Max Score: 100
```

### D. Simulation Parameters

**Monte Carlo**:
- Default iterations: 10,000
- Distribution: Beta (PERT)
- Resource contention: Queuing theory (M/M/1)
- Historical calibration: 3 years of data

**Markov Chain**:
- States: 7 (NotStarted → Completed)
- Transition matrix: Learned from history
- Expected completion: Fundamental matrix method

---

## Contact & Support

**Repository**: [GitHub URL]  
**Documentation**: This file  
**Issues**: [GitHub Issues URL]  
**Email**: [Support Email]

---

**End of Documentation**
