"""JWT authentication middleware for Supabase-issued tokens.

Provides ``get_current_user`` — an async FastAPI dependency that extracts a
Bearer token from the Authorization header, verifies it using the Supabase
JWKS endpoint (ES256) or ``SUPABASE_JWT_SECRET`` (HS256 legacy), and returns
the ``sub`` claim (user_id UUID string).
"""

import logging
import os
import time
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwk, jwt

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Cached JWKS keys: list of jose JWK key objects
_jwks_cache: list = []
_jwks_fetched_at: float = 0
_JWKS_TTL = 3600  # re-fetch every hour


def _get_supabase_url() -> str:
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
    return url.rstrip("/")


def _fetch_jwks() -> list:
    """Fetch JWKS from Supabase and return list of key dicts."""
    global _jwks_cache, _jwks_fetched_at

    if _jwks_cache and (time.time() - _jwks_fetched_at) < _JWKS_TTL:
        return _jwks_cache

    import urllib.request
    import json

    supabase_url = _get_supabase_url()
    if not supabase_url:
        return []

    try:
        url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        _jwks_cache = data.get("keys", [])
        _jwks_fetched_at = time.time()
        logger.info("Fetched %d JWKS keys from Supabase", len(_jwks_cache))
    except Exception as e:
        logger.warning("Failed to fetch JWKS: %s", e)

    return _jwks_cache


def _get_signing_key(token: str) -> tuple:
    """Determine the signing key and algorithm for a token.

    Returns (key, algorithms) tuple.
    """
    header = jwt.get_unverified_header(token)
    alg = header.get("alg", "HS256")

    if alg == "ES256":
        kid = header.get("kid")
        keys = _fetch_jwks()
        for key_data in keys:
            if key_data.get("kid") == kid:
                key = jwk.construct(key_data, algorithm="ES256")
                return key, ["ES256"]
        raise JWTError(f"No matching JWKS key for kid={kid}")

    # Fallback to HS256 with shared secret
    secret = os.environ.get("SUPABASE_JWT_SECRET")
    if not secret:
        raise ValueError("SUPABASE_JWT_SECRET environment variable is not set")
    return secret, ["HS256"]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """FastAPI dependency that verifies a Supabase JWT and returns the user_id.

    Returns:
        The ``sub`` claim (user_id UUID string) from the verified JWT.

    Raises:
        HTTPException 401: Token expired, invalid signature, malformed, or
            missing ``sub`` claim.
        HTTPException 403: No Authorization header (raised by ``HTTPBearer``).
    """
    token = credentials.credentials
    try:
        key, algorithms = _get_signing_key(token)
        payload = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience="authenticated",
        )
    except ExpiredSignatureError:
        logger.warning("auth_failed: token_expired")
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError as e:
        logger.warning("auth_failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing sub claim")
    return user_id
