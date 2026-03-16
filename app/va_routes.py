"""
VA Lighthouse API Router
Provides live claim status lookups via the VA Benefits Claims API v1.
OAuth2 CCG (Client Credentials Grant) — VA Sandbox: sandbox-api.va.gov
Rate limit: 60 req/min per token; handled via Retry-After header.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/va", tags=["va-lighthouse"])

# ── Token cache (in-process, reused across warm invocations) ─────────
_token_cache: dict[str, Any] = {"access_token": None, "expires_at": 0}

VA_TOKEN_URL  = "https://sandbox-api.va.gov/oauth2/benefits-claims/v1/token"
VA_CLAIMS_URL = "https://sandbox-api.va.gov/services/claims/v1/claims"


async def _get_access_token() -> str:
    """Return a cached CCG access token, refreshing if expired."""
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 30:
        return _token_cache["access_token"]

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            VA_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.va_client_id,
                "client_secret": settings.va_client_secret,
                "scope": "claim.read",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if resp.status_code != 200:
        logger.error("VA token error %s: %s", resp.status_code, resp.text[:200])
        raise HTTPException(status_code=502, detail="VA authentication failed.")

    data = resp.json()
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600)
    return _token_cache["access_token"]


async def _va_get(path: str, params: dict | None = None) -> dict:
    """GET from VA Lighthouse with rate-limit handling."""
    token = await _get_access_token()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"https://sandbox-api.va.gov{path}",
            params=params,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )

    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", 60))
        raise HTTPException(
            status_code=429,
            detail=f"VA API rate limit reached. Retry after {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Claim not found.")
    if not resp.is_success:
        logger.error("VA API error %s: %s", resp.status_code, resp.text[:200])
        raise HTTPException(status_code=502, detail="VA API error.")

    return resp.json()


# ── Schemas ───────────────────────────────────────────────────────────

class ClaimStatusResponse(BaseModel):
    claim_id: str
    status: str
    claim_type: str | None = None
    date_filed: str | None = None
    development_letter_sent: bool | None = None
    decision_letter_sent: bool | None = None
    phase: int | None = None
    phase_change_date: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("/claims", summary="List all claims for the authenticated veteran")
async def list_claims(request: Request):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required.")
    data = await _va_get("/services/claims/v1/claims")
    return data


@router.get("/claims/{claim_id}", response_model=ClaimStatusResponse)
async def get_claim_status(claim_id: str, request: Request):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required.")
    data = await _va_get(f"/services/claims/v1/claims/{claim_id}")
    attrs = data.get("data", {}).get("attributes", {})
    return ClaimStatusResponse(
        claim_id=claim_id,
        status=attrs.get("status", "unknown"),
        claim_type=attrs.get("claimType"),
        date_filed=attrs.get("dateFiled"),
        development_letter_sent=attrs.get("developmentLetterSent"),
        decision_letter_sent=attrs.get("decisionLetterSent"),
        phase=attrs.get("phase"),
        phase_change_date=attrs.get("phaseChangeDate"),
    )
