"""Positions and account endpoints.

These are fast enough for inline execution via asyncio.to_thread()
— no submit/poll pattern needed.
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException

from apps.api.schemas import (
    AccountResponse,
    PositionSchema,
    PositionsResponse,
    WheelStateEntry,
)
from apps.api.services.auth import get_current_user
from apps.api.services.clients import create_alpaca_clients
from apps.api.services.database import get_db
from apps.api.services.key_retrieval import retrieve_alpaca_keys

from core.state_manager import calculate_risk, update_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["positions"])


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------


@router.get("/positions", response_model=PositionsResponse)
async def get_positions(
    user_id: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """Fetch current positions with wheel state classification.

    Uses JWT auth to identify the user, retrieves encrypted Alpaca keys
    from the DB, and fetches positions via the Alpaca API.
    """
    api_key, secret_key, is_paper = await retrieve_alpaca_keys(user_id, db)

    trade_client, _, _ = create_alpaca_clients(
        api_key=api_key,
        secret_key=secret_key,
        is_paper=is_paper,
    )

    try:
        positions = await asyncio.to_thread(trade_client.get_all_positions)
    except Exception as exc:
        logger.error("Failed to fetch positions: %s", exc)
        raise HTTPException(status_code=502, detail=f"Alpaca API error: {exc}")

    # Build position list
    pos_list = [
        PositionSchema(
            symbol=p.symbol,
            qty=str(p.qty),
            avg_entry_price=str(p.avg_entry_price),
            market_value=str(p.market_value) if p.market_value else None,
            asset_class=str(p.asset_class),
            side=str(p.side) if hasattr(p, "side") and p.side else None,
        )
        for p in positions
    ]

    # Classify wheel state
    try:
        state = update_state(positions)
    except ValueError as exc:
        logger.warning("State classification error: %s", exc)
        raise HTTPException(status_code=422, detail=f"State error: {exc}")

    wheel_state = {
        sym: WheelStateEntry(**data)
        for sym, data in state.items()
    }

    return PositionsResponse(positions=pos_list, wheel_state=wheel_state)


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------


@router.get("/account", response_model=AccountResponse)
async def get_account(
    user_id: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """Fetch account summary with capital at risk.

    Returns buying power, portfolio value, cash, and total capital at risk
    computed from current positions.
    """
    api_key, secret_key, is_paper = await retrieve_alpaca_keys(user_id, db)

    trade_client, _, _ = create_alpaca_clients(
        api_key=api_key,
        secret_key=secret_key,
        is_paper=is_paper,
    )

    try:
        account = await asyncio.to_thread(trade_client.get_account)
        positions = await asyncio.to_thread(trade_client.get_all_positions)
    except Exception as exc:
        logger.error("Failed to fetch account data: %s", exc)
        raise HTTPException(status_code=502, detail=f"Alpaca API error: {exc}")

    risk = calculate_risk(positions)

    return AccountResponse(
        buying_power=str(account.buying_power),
        portfolio_value=str(account.portfolio_value),
        cash=str(account.cash),
        capital_at_risk=risk,
    )
