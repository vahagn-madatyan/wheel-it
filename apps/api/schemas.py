"""Pydantic request/response models for the screening API.

Mirrors the dataclass fields from PutRecommendation and CallRecommendation
so the OpenAPI schema is accurate and explicit.
"""

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Screening request models
# ---------------------------------------------------------------------------


class PutScreenRequest(BaseModel):
    """Request body for submitting a put screening run."""

    symbols: list[str] = Field(..., min_length=1, description="Underlying tickers to screen")
    buying_power: float = Field(..., gt=0, description="Available cash for securing puts")
    preset: str = Field("moderate", description="Screener preset: conservative, moderate, aggressive")


class CallScreenRequest(BaseModel):
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
# Positions / Account response schemas
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Key management schemas (S02 — encrypted key storage)
# ---------------------------------------------------------------------------


class KeyStoreRequest(BaseModel):
    """Request body for storing an API key (plaintext — encrypted at rest)."""

    key_value: str = Field(..., description="Plaintext API key value to store")
    key_name: str = Field(
        ...,
        description="Key identifier: 'api_key' or 'secret_key' (alpaca), 'api_key' (finnhub)",
    )
    is_paper: Optional[bool] = Field(
        None, description="Paper trading flag (only used for alpaca provider)"
    )


class KeyStatusItem(BaseModel):
    """Status of a single provider's stored keys — never exposes values."""

    provider: str
    connected: bool
    is_paper: Optional[bool] = None
    key_names: list[str] = Field(
        ..., description='Which key names are stored, e.g. ["api_key", "secret_key"]'
    )


class KeyStatusResponse(BaseModel):
    """Aggregate status of all stored providers."""

    providers: list[KeyStatusItem]


class KeyVerifyResponse(BaseModel):
    """Result of verifying a provider's stored credentials."""

    provider: str
    valid: bool
    error: Optional[str] = None
