"""Key management CRUD endpoints (S02).

Integrates encryption (T01), database (T02), and auth (T03) to provide
secure API key storage, status, deletion, and verification.

All endpoints require Supabase JWT authentication via ``get_current_user``.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from apps.api.schemas import (
    KeyStoreRequest,
    KeyStatusItem,
    KeyStatusResponse,
    KeyVerifyResponse,
)
from apps.api.services.auth import get_current_user
from apps.api.services.database import get_db
from apps.api.services.encryption import decrypt_value, encrypt_value

logger = logging.getLogger(__name__)

VALID_PROVIDERS = {"alpaca", "finnhub"}
VALID_KEY_NAMES: dict[str, set[str]] = {
    "alpaca": {"api_key", "secret_key"},
    "finnhub": {"api_key"},
}

router = APIRouter(prefix="/api/keys", tags=["keys"])


def _validate_provider(provider: str) -> None:
    """Raise 422 if provider is not recognised."""
    if provider not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid provider '{provider}'. Must be one of: {sorted(VALID_PROVIDERS)}",
        )


# ---- POST /{provider} — store an API key --------------------------------

@router.post("/{provider}")
async def store_key(
    provider: str,
    request: KeyStoreRequest,
    user_id: str = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db),
) -> dict[str, str]:
    """Encrypt and upsert an API key for *provider*."""
    _validate_provider(provider)

    allowed = VALID_KEY_NAMES[provider]
    if request.key_name not in allowed:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid key_name '{request.key_name}' for provider '{provider}'. "
                f"Allowed: {sorted(allowed)}"
            ),
        )

    encrypted_value, encrypted_dek, nonce, dek_nonce = encrypt_value(
        request.key_value
    )

    await db.execute(
        """
        INSERT INTO api_keys (user_id, provider, key_name, encrypted_value,
                              encrypted_dek, nonce, dek_nonce, is_paper)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (user_id, provider, key_name)
        DO UPDATE SET encrypted_value = $4,
                      encrypted_dek   = $5,
                      nonce           = $6,
                      dek_nonce       = $7,
                      is_paper        = $8,
                      updated_at      = now()
        """,
        user_id,
        provider,
        request.key_name,
        encrypted_value,
        encrypted_dek,
        nonce,
        dek_nonce,
        request.is_paper,
    )

    logger.info(
        "key_stored",
        extra={"provider": provider, "key_name": request.key_name, "user_id": user_id},
    )
    return {"status": "stored", "provider": provider, "key_name": request.key_name}


# ---- GET /status — list stored providers ---------------------------------

@router.get("/status", response_model=KeyStatusResponse)
async def get_key_status(
    user_id: str = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db),
) -> KeyStatusResponse:
    """Return which providers have keys stored — never returns key values."""
    rows = await db.fetch(
        "SELECT provider, key_name, is_paper FROM api_keys WHERE user_id = $1",
        user_id,
    )

    # Group rows by provider
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        prov = row["provider"]
        if prov not in grouped:
            grouped[prov] = {"is_paper": row["is_paper"], "key_names": []}
        grouped[prov]["key_names"].append(row["key_name"])

    providers = [
        KeyStatusItem(
            provider=prov,
            connected=True,
            is_paper=info["is_paper"],
            key_names=sorted(info["key_names"]),
        )
        for prov, info in sorted(grouped.items())
    ]
    return KeyStatusResponse(providers=providers)


# ---- DELETE /{provider} — remove all keys for a provider -----------------

@router.delete("/{provider}")
async def delete_keys(
    provider: str,
    user_id: str = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db),
) -> dict[str, str]:
    """Delete all stored keys for *provider*."""
    _validate_provider(provider)

    await db.execute(
        "DELETE FROM api_keys WHERE user_id = $1 AND provider = $2",
        user_id,
        provider,
    )

    logger.info(
        "key_deleted", extra={"provider": provider, "user_id": user_id}
    )
    return {"status": "deleted", "provider": provider}


# ---- POST /{provider}/verify — test key connectivity ---------------------

@router.post("/{provider}/verify", response_model=KeyVerifyResponse)
async def verify_keys(
    provider: str,
    user_id: str = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db),
) -> KeyVerifyResponse:
    """Fetch, decrypt, and test stored keys for *provider*."""
    _validate_provider(provider)

    rows = await db.fetch(
        """
        SELECT key_name, encrypted_value, encrypted_dek, nonce, dek_nonce, is_paper
        FROM api_keys
        WHERE user_id = $1 AND provider = $2
        """,
        user_id,
        provider,
    )

    if not rows:
        return KeyVerifyResponse(
            provider=provider, valid=False, error="No keys stored for this provider"
        )

    # Decrypt all stored keys into a dict keyed by key_name
    decrypted: dict[str, str] = {}
    is_paper = True
    try:
        for row in rows:
            plaintext = decrypt_value(
                bytes(row["encrypted_value"]),
                bytes(row["encrypted_dek"]),
                bytes(row["nonce"]),
                bytes(row["dek_nonce"]),
            )
            decrypted[row["key_name"]] = plaintext
            if row["is_paper"] is not None:
                is_paper = row["is_paper"]
    except Exception:
        logger.warning(
            "key_verify_decrypt_failed",
            extra={"provider": provider, "user_id": user_id},
        )
        return KeyVerifyResponse(
            provider=provider, valid=False, error="Failed to decrypt stored keys"
        )

    try:
        if provider == "alpaca":
            api_key = decrypted.get("api_key")
            secret_key = decrypted.get("secret_key")
            if not api_key or not secret_key:
                return KeyVerifyResponse(
                    provider=provider,
                    valid=False,
                    error="Alpaca requires both api_key and secret_key",
                )
            from alpaca.trading.client import TradingClient

            client = TradingClient(
                api_key=api_key, secret_key=secret_key, paper=is_paper
            )
            await asyncio.to_thread(client.get_account)

        elif provider == "finnhub":
            api_key = decrypted.get("api_key")
            if not api_key:
                return KeyVerifyResponse(
                    provider=provider,
                    valid=False,
                    error="Finnhub requires an api_key",
                )
            import finnhub

            client = finnhub.Client(api_key=api_key)
            await asyncio.to_thread(client.market_status, exchange="US")

    except Exception as exc:
        logger.info(
            "key_verified",
            extra={"provider": provider, "user_id": user_id, "valid": False},
        )
        return KeyVerifyResponse(
            provider=provider, valid=False, error=str(exc)
        )

    logger.info(
        "key_verified",
        extra={"provider": provider, "user_id": user_id, "valid": True},
    )
    return KeyVerifyResponse(provider=provider, valid=True)
