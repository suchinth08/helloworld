"""
Congress Twin FastAPI application.

NVS-GenAI: Lifespan for DB/client init; async-first.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request

# Ensure congress_twin loggers (e.g. chat_intent) show INFO in uvicorn output
_ct_log = logging.getLogger("congress_twin")
_ct_log.setLevel(logging.INFO)
if not _ct_log.handlers:
    _h = logging.StreamHandler()
    _h.setLevel(logging.INFO)
    _h.setFormatter(logging.Formatter("%(levelname)s:     %(name)s — %(message)s"))
    _ct_log.addHandler(_h)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from congress_twin.config import get_settings
from congress_twin.api.v1.planner import router as planner_router
from congress_twin.api.v1.csv_import import router as import_router
from congress_twin.api.v1.simulation import router as simulation_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Init resources at startup; cleanup on shutdown."""
    settings = get_settings()
    # SQLite DB is initialized on first use (get_engine() in planner_repo/events_repo)
    yield
    # TODO: close connections in lifecycle/shutdown


app = FastAPI(
    title="Congress Twin API",
    description="Planner execution + OR/agents (Base view APIs)",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Ensure error responses include proper JSON and CORS headers (avoids CORS errors in browser)."""
    origin = request.headers.get("origin", "*")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


settings = get_settings()
# Build allowed origins: when allow_all, use *; else ensure localhost is always allowed for dev
if settings.cors_allow_all:
    origins: list[str] = ["*"]
    credentials = False
else:
    origins = list(settings.cors_origins_list)
    # Ensure localhost / 127.0.0.1 are allowed when frontend runs on same machine or different host
    for o in ("http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3003", "http://127.0.0.1:3003"):
        if o not in origins:
            origins.append(o)
    credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(planner_router, prefix="/api/v1/planner", tags=["planner"])
app.include_router(import_router, prefix="/api/v1/import", tags=["import"])
app.include_router(simulation_router, prefix="/api/v1/simulation", tags=["simulation"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "congress-twin"}
