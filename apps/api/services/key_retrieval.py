"""Shared helper for retrieving and decrypting Alpaca API keys from the DB.

Extracts the decrypt-and-validate pattern from ``keys.py:verify_keys``
into a reusable function for any endpoint that needs Alpaca credentials.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException

from apps.api.services.encryption import decrypt_value

logger = logging.getLogger(__name__)


async def retrieve_alpaca_keys(
    user_id: str,
    db,  # asyncpg.Connection
) -> tuple[str, str, bool]:
    """Fetch, decrypt, and validate stored Alpaca keys for a user.

    Returns:
        A 3-tuple ``(api_key, secret_key, is_paper)``.
        ``is_paper`` defaults to ``True`` if not stored.

    Raises:
        HTTPException 400: No keys stored, incomplete key set, or
            decryption failure.
    """
    rows = await db.fetch(
        """
        SELECT key_name, encrypted_value, encrypted_dek, nonce, dek_nonce, is_paper
        FROM api_keys
        WHERE user_id = $1 AND provider = 'alpaca'
        """,
        user_id,
    )

    if not rows:
        raise HTTPException(
            status_code=400,
            detail="Alpaca API keys not configured. Add keys in Settings.",
        )

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
            "key_retrieval_decrypt_failed",
            extra={"provider": "alpaca", "user_id": user_id},
        )
        raise HTTPException(
            status_code=400,
            detail="Failed to decrypt stored keys",
        )

    api_key = decrypted.get("api_key")
    secret_key = decrypted.get("secret_key")

    if not api_key or not secret_key:
        raise HTTPException(
            status_code=400,
            detail="Alpaca requires both api_key and secret_key",
        )

    logger.info(
        "keys_retrieved",
        extra={"provider": "alpaca", "user_id": user_id},
    )

    return api_key, secret_key, is_paper
