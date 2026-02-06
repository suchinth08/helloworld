"""
Congress Twin FastAPI application.

NVS-GenAI: Lifespan for DB/client init; async-first.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from congress_twin.config import get_settings
from congress_twin.api.v1.planner import router as planner_router


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

settings = get_settings()
if settings.cors_allow_all:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(planner_router, prefix="/api/v1/planner", tags=["planner"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "congress-twin"}
