"""FastAPI application entry point.

Start with:
    cd /path/to/wheeely && PYTHONPATH=. uvicorn apps.api.main:app --reload
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.services.task_store import TaskStore, periodic_cleanup
from apps.api.routers import screen, positions


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle: start TTL cleanup task, cancel on shutdown."""
    store = TaskStore()
    app.state.task_store = store

    cleanup_task = asyncio.create_task(periodic_cleanup(store, interval=300))

    yield

    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Wheeely Screening API",
    description="HTTP wrapper around the options wheel screener engine",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow all origins for dev; S07 will tighten this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(screen.router)
app.include_router(positions.router)
