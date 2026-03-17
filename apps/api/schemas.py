"""Pydantic request/response models for the screening API.

Mirrors the dataclass fields from PutRecommendation and CallRecommendation
so the OpenAPI schema is accurate and explicit.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared mixin for Alpaca credentials
# ---------------------------------------------------------------------------


class AlpacaKeysMixin(BaseModel):
    """Base model carrying Alpaca API credentials per request."""

    alpaca_api_key: str = Field(..., description="Alpaca API key")
    alpaca_secret_key: str = Field(..., description="Alpaca secret key")
    is_paper: bool = Field(True, description="Use paper trading environment")


# ---------------------------------------------------------------------------
# Screening request models
# ---------------------------------------------------------------------------


class PutScreenRequest(AlpacaKeysMixin):
    """Request body for submitting a put screening run."""

    symbols: list[str] = Field(..., min_length=1, description="Underlying tickers to screen")
    buying_power: float = Field(..., gt=0, description="Available cash for securing puts")
    preset: str = Field("moderate", description="Screener preset: conservative, moderate, aggressive")


class CallScreenRequest(AlpacaKeysMixin):
    """Request body for submitting a call screening run."""

    symbol: str = Field(..., description="Underlying ticker for covered calls")
    cost_basis: float = Field(..., gt=0, description="Average entry price of shares")
    preset: str = Field("moderate", description="Screener preset: conservative, moderate, aggressive")


# ---------------------------------------------------------------------------
# Screening result schemas
# ---------------------------------------------------------------------------


class PutResultSchema(BaseModel):
    """Single put recommendation — mirrors PutRecommendation dataclass."""

    symbol: str
    underlying: str
    strike: float
    dte: int
    premium: float
    delta: Optional[float] = None
    oi: int
    spread: float
    annualized_return: float


class CallResultSchema(BaseModel):
    """Single call recommendation — mirrors CallRecommendation dataclass."""

    symbol: str
    underlying: str
    strike: float
    dte: int
    premium: float
    delta: Optional[float] = None
    oi: int
    spread: float
    annualized_return: float
    cost_basis: float


# ---------------------------------------------------------------------------
# Run submit / status responses
# ---------------------------------------------------------------------------


class RunSubmitResponse(BaseModel):
    """Returned immediately after submitting a screening run."""

    run_id: str
    status: str


class RunStatusResponse(BaseModel):
    """Full status of a screening run (poll endpoint)."""

    run_id: str
    status: str
    run_type: str
    results: Optional[list[PutResultSchema] | list[CallResultSchema]] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Positions / Account query params and responses
# ---------------------------------------------------------------------------


class PositionsQuery(BaseModel):
    """Query parameters for the positions endpoint."""

    alpaca_api_key: str
    alpaca_secret_key: str
    is_paper: bool = True


class AccountQuery(BaseModel):
    """Query parameters for the account endpoint."""

    alpaca_api_key: str
    alpaca_secret_key: str
    is_paper: bool = True


class PositionSchema(BaseModel):
    """Single position with wheel state info."""

    symbol: str
    qty: str
    avg_entry_price: str
    market_value: Optional[str] = None
    asset_class: str
    side: Optional[str] = None


class WheelStateEntry(BaseModel):
    """Wheel state for one underlying symbol."""

    type: str
    price: Optional[float] = None
    qty: Optional[int] = None


class PositionsResponse(BaseModel):
    """Response from the positions endpoint."""

    positions: list[PositionSchema]
    wheel_state: dict[str, WheelStateEntry]


class AccountResponse(BaseModel):
    """Response from the account endpoint."""

    buying_power: str
    portfolio_value: str
    cash: str
    capital_at_risk: float
