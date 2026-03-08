"""
Valor Assist — Cognito JWT Token Verification

Verifies AWS Cognito JWT tokens sent by the frontend. Works alongside
the existing custom JWT auth system — the backend accepts either:

  1. Cognito ID tokens (issued by Cognito User Pool)
  2. Legacy HS256 tokens (issued by our auth.py)

Cognito tokens are RS256-signed JWTs verified against the Cognito
JWKS (JSON Web Key Set) endpoint. The public keys are cached to
avoid repeated network calls.

Security:
  - Validates token signature against Cognito public keys
  - Checks issuer matches the configured User Pool
  - Checks audience matches the configured App Client ID
  - Checks token expiration
  - Checks token_use claim (id vs access)
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
import jwt
from jwt import PyJWKClient

from app.config import settings

logger = logging.getLogger(__name__)

# Cache the JWKS client to avoid re-fetching keys on every request.
_jwks_client: PyJWKClient | None = None
_jwks_client_initialized_at: float = 0
JWKS_CACHE_TTL = 3600  # Re-initialize JWKS client every hour


def _get_jwks_client() -> PyJWKClient | None:
    """
    Get or create a cached PyJWKClient for the configured Cognito User Pool.
    Returns None if Cognito is not configured.
    """
    global _jwks_client, _jwks_client_initialized_at

    if not settings.cognito_user_pool_id or not settings.cognito_region:
        return None

    now = time.time()
    if _jwks_client is None or (now - _jwks_client_initialized_at) > JWKS_CACHE_TTL:
        jwks_url = (
            f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/"
            f"{settings.cognito_user_pool_id}/.well-known/jwks.json"
        )
        _jwks_client = PyJWKClient(jwks_url)
        _jwks_client_initialized_at = now
        logger.info("Initialized Cognito JWKS client for pool %s", settings.cognito_user_pool_id)

    return _jwks_client


def decode_cognito_token(token: str) -> dict[str, Any] | None:
    """
    Decode and verify a Cognito JWT token.

    Validates:
      - Signature (RS256 against Cognito JWKS)
      - Issuer (must match configured User Pool)
      - Audience (must match configured App Client ID)
      - Expiration
      - token_use claim (accepts both 'id' and 'access')

    Returns the decoded payload on success, None on failure.
    """
    jwks_client = _get_jwks_client()
    if jwks_client is None:
        return None

    expected_issuer = (
        f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/"
        f"{settings.cognito_user_pool_id}"
    )

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=expected_issuer,
            audience=settings.cognito_app_client_id,
            options={"require": ["exp", "iss", "sub"]},
        )

        # Verify token_use claim
        token_use = payload.get("token_use")
        if token_use not in ("id", "access"):
            logger.warning("Invalid token_use claim: %s", token_use)
            return None

        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Cognito token expired")
        return None
    except jwt.InvalidTokenError as exc:
        logger.warning("Invalid Cognito token: %s", exc)
        return None
    except Exception as exc:
        logger.error("Unexpected error verifying Cognito token: %s", exc)
        return None


def is_cognito_token(token: str) -> bool:
    """
    Heuristic check: Cognito tokens are RS256-signed JWTs with a
    specific issuer format. Peek at the header without verification
    to determine which verification path to use.
    """
    try:
        header = jwt.get_unverified_header(token)
        return header.get("alg") == "RS256" and header.get("kid") is not None
    except Exception:
        return False
