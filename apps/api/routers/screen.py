"""Screening endpoints: submit put/call screening runs and poll for results.

Uses submit→poll pattern to avoid HTTP timeouts on 30-60s screener runs.
Background work runs via asyncio.to_thread() to keep the event loop free.
"""

import asyncio
import logging

from dataclasses import asdict
from fastapi import APIRouter, HTTPException, Request

from apps.api.schemas import (
    CallScreenRequest,
    PutScreenRequest,
    RunSubmitResponse,
    RunStatusResponse,
    PutResultSchema,
    CallResultSchema,
)
from apps.api.services.clients import create_alpaca_clients
from apps.api.services.task_store import TaskStatus

from screener.config_loader import ScreenerConfig, load_preset
from screener.put_screener import screen_puts
from screener.call_screener import screen_calls

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/screen", tags=["screening"])


def _get_task_store(request: Request):
    """Retrieve the shared TaskStore from app state."""
    return request.app.state.task_store


# ---------------------------------------------------------------------------
# PUT screening
# ---------------------------------------------------------------------------


@router.post("/puts", response_model=RunSubmitResponse, status_code=202)
async def submit_put_screen(body: PutScreenRequest, request: Request):
    """Submit a put screening run.

    Returns 202 immediately with a run_id. Poll GET /api/screen/runs/{run_id}
    for status and results.
    """
    store = _get_task_store(request)

    # Validate preset and build config server-side
    try:
        preset_data = load_preset(body.preset)
        config = ScreenerConfig(**preset_data)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Create per-request Alpaca clients
    trade_client, option_client, stock_client = create_alpaca_clients(
        api_key=body.alpaca_api_key,
        secret_key=body.alpaca_secret_key,
        is_paper=body.is_paper,
    )

    run_id = store.submit("put_screen")

    # Launch background screening coroutine
    asyncio.ensure_future(
        _run_put_screen(
            store, run_id, trade_client, option_client,
            body.symbols, body.buying_power, config, stock_client,
        )
    )

    return RunSubmitResponse(run_id=run_id, status=TaskStatus.PENDING.value)


async def _run_put_screen(
    store, run_id, trade_client, option_client,
    symbols, buying_power, config, stock_client,
):
    """Background wrapper: runs screen_puts in a thread and captures results/errors."""
    store.update(run_id, TaskStatus.RUNNING)
    try:
        results = await asyncio.to_thread(
            screen_puts,
            trade_client, option_client, symbols,
            buying_power, config, stock_client,
        )
        serialized = [asdict(r) for r in results]
        store.update(run_id, TaskStatus.COMPLETED, results=serialized)
        logger.info("Put screen run %s completed: %d results", run_id, len(results))
    except Exception as exc:
        store.update(run_id, TaskStatus.FAILED, error=str(exc))
        logger.error("Put screen run %s failed: %s", run_id, exc)


# ---------------------------------------------------------------------------
# CALL screening
# ---------------------------------------------------------------------------


@router.post("/calls", response_model=RunSubmitResponse, status_code=202)
async def submit_call_screen(body: CallScreenRequest, request: Request):
    """Submit a call screening run.

    Returns 202 immediately with a run_id. Poll GET /api/screen/runs/{run_id}
    for status and results.
    """
    store = _get_task_store(request)

    try:
        preset_data = load_preset(body.preset)
        config = ScreenerConfig(**preset_data)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    trade_client, option_client, _ = create_alpaca_clients(
        api_key=body.alpaca_api_key,
        secret_key=body.alpaca_secret_key,
        is_paper=body.is_paper,
    )

    run_id = store.submit("call_screen")

    asyncio.ensure_future(
        _run_call_screen(
            store, run_id, trade_client, option_client,
            body.symbol, body.cost_basis, config,
        )
    )

    return RunSubmitResponse(run_id=run_id, status=TaskStatus.PENDING.value)


async def _run_call_screen(
    store, run_id, trade_client, option_client,
    symbol, cost_basis, config,
):
    """Background wrapper: runs screen_calls in a thread and captures results/errors."""
    store.update(run_id, TaskStatus.RUNNING)
    try:
        results = await asyncio.to_thread(
            screen_calls,
            trade_client, option_client, symbol, cost_basis, config,
        )
        serialized = [asdict(r) for r in results]
        store.update(run_id, TaskStatus.COMPLETED, results=serialized)
        logger.info("Call screen run %s completed: %d results", run_id, len(results))
    except Exception as exc:
        store.update(run_id, TaskStatus.FAILED, error=str(exc))
        logger.error("Call screen run %s failed: %s", run_id, exc)


# ---------------------------------------------------------------------------
# Poll endpoint
# ---------------------------------------------------------------------------


@router.get("/runs/{run_id}", response_model=RunStatusResponse)
async def get_run_status(run_id: str, request: Request):
    """Poll status and results of a screening run.

    Returns 404 if run_id is unknown.
    """
    store = _get_task_store(request)
    entry = store.get(run_id)

    if entry is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    # Build typed result list based on run_type
    results = None
    if entry.results is not None:
        if entry.run_type == "put_screen":
            results = [PutResultSchema(**r) for r in entry.results]
        elif entry.run_type == "call_screen":
            results = [CallResultSchema(**r) for r in entry.results]

    return RunStatusResponse(
        run_id=entry.run_id,
        status=entry.status.value,
        run_type=entry.run_type,
        results=results,
        error=entry.error,
    )
