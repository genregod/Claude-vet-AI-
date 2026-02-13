"""
Valor Assist — VA.gov Lighthouse API Integration

Provides secure access to the veteran's own data through the VA's
official APIs. This is how we pull medical records, claims status,
and service history — with the veteran's explicit OAuth2 consent.

VA Lighthouse API (https://developer.va.gov):
  - Veterans Health API   → medical records, conditions, medications
  - Benefits Claims API   → claim status, decision letters
  - Veteran Verification  → service history, disability rating

Authentication flow:
  1. Veteran authorizes access via VA.gov OAuth2 consent screen
  2. VA issues an access token scoped to the veteran's data
  3. We use that token to pull ONLY what the veteran consented to
  4. All fetched data is encrypted (PII Shield) before storage
  5. Every access is audit-logged

This module NEVER stores VA credentials. Tokens are short-lived and
only held in encrypted session state during the active evaluation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

import httpx

from app.config import settings
from app.pii_shield import audit_log, field_encryptor, AuditEntry

logger = logging.getLogger(__name__)


# ── VA API scopes and endpoints ──────────────────────────────────────

class VAScope(str, Enum):
    """OAuth2 scopes for VA Lighthouse APIs."""
    PROFILE = "profile"
    SERVICE_HISTORY = "service_history.read"
    DISABILITY_RATING = "disability_rating.read"
    VETERAN_STATUS = "veteran_status.read"
    CLAIMS = "claim.read"
    HEALTH_RECORDS = "patient/Patient.read"
    CONDITIONS = "patient/Condition.read"
    MEDICATIONS = "patient/MedicationRequest.read"


# VA Lighthouse base URLs
VA_SANDBOX_BASE = "https://sandbox-api.va.gov"
VA_PRODUCTION_BASE = "https://api.va.gov"

VA_OAUTH_AUTHORIZE = "/oauth2/veteran/v1/authorization"
VA_OAUTH_TOKEN = "/oauth2/veteran/v1/token"

# API paths
VA_CLAIMS_PATH = "/claims/v2/veterans/{icn}/claims"
VA_RATING_PATH = "/veteran_verification/v2/disability_rating"
VA_SERVICE_HISTORY_PATH = "/veteran_verification/v2/service_history"
VA_STATUS_PATH = "/veteran_verification/v2/status"
VA_HEALTH_CONDITIONS_PATH = "/services/fhir/v0/r4/Condition"
VA_HEALTH_MEDICATIONS_PATH = "/services/fhir/v0/r4/MedicationRequest"


@dataclass
class VACredentials:
    """Short-lived VA API credentials for a single veteran session."""
    va_access_token: str
    va_refresh_token: str = ""
    va_token_expires_at: float = 0
    icn: str = ""  # VA Integration Control Number (unique patient ID)
    scopes: list[str] = field(default_factory=list)


# ── VA OAuth2 client ─────────────────────────────────────────────────

class VALighthouseClient:
    """
    Manages the OAuth2 flow with VA.gov and subsequent API calls.

    The veteran must explicitly authorize each scope. We request the
    minimum scopes needed for claim evaluation.
    """

    def __init__(self):
        self._base_url = (
            VA_SANDBOX_BASE if settings.va_api_sandbox else VA_PRODUCTION_BASE
        )
        self._client_id = settings.va_api_client_id
        self._redirect_uri = settings.va_api_redirect_uri

    def get_authorization_url(
        self, state: str, scopes: list[VAScope] | None = None,
    ) -> str:
        """
        Generate the VA.gov OAuth2 authorization URL.

        The veteran is redirected here to consent to data sharing.
        VA.gov handles the actual authentication (via DS Logon, ID.me,
        Login.gov, or My HealtheVet credentials).
        """
        requested_scopes = scopes or [
            VAScope.PROFILE,
            VAScope.DISABILITY_RATING,
            VAScope.SERVICE_HISTORY,
            VAScope.CLAIMS,
            VAScope.CONDITIONS,
        ]
        scope_str = " ".join(s.value for s in requested_scopes)

        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": scope_str,
            "state": state,
        }
        return (
            f"{self._base_url}{VA_OAUTH_AUTHORIZE}?"
            + "&".join(f"{k}={v}" for k, v in params.items())
        )

    async def exchange_code(self, code: str) -> VACredentials:
        """Exchange the authorization code for VA API tokens."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self._base_url}{VA_OAUTH_TOKEN}",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self._redirect_uri,
                    "client_id": self._client_id,
                    "client_secret": settings.va_api_client_secret,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return VACredentials(
            va_access_token=data["access_token"],
            va_refresh_token=data.get("refresh_token", ""),
            va_token_expires_at=data.get("expires_at", 0),
            icn=data.get("patient", ""),
            scopes=data.get("scope", "").split(),
        )

    # ── Data fetchers ────────────────────────────────────────────────

    async def _get(
        self, path: str, creds: VACredentials,
        params: dict | None = None,
    ) -> dict:
        """Authenticated GET against VA Lighthouse."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self._base_url}{path}",
                headers={
                    "Authorization": f"Bearer {creds.va_access_token}",
                    "apikey": settings.va_api_key,
                },
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_disability_rating(
        self, creds: VACredentials, user_id: str,
    ) -> dict:
        """Fetch the veteran's combined disability rating."""
        audit_log.record(AuditEntry(
            user_id=user_id,
            action="read",
            data_class="phi",
            field_name="disability_rating",
            resource_id=f"va:{creds.icn}",
            reason="case_evaluation",
        ))

        data = await self._get(VA_RATING_PATH, creds)

        # Encrypt the fetched data before returning
        return field_encryptor.encrypt_dict(
            data.get("data", {}).get("attributes", {}),
            user_id=user_id,
            resource_id=f"va:{creds.icn}",
        )

    async def get_service_history(
        self, creds: VACredentials, user_id: str,
    ) -> list[dict]:
        """Fetch the veteran's service history (branches, dates, discharge)."""
        audit_log.record(AuditEntry(
            user_id=user_id,
            action="read",
            data_class="pii",
            field_name="service_history",
            resource_id=f"va:{creds.icn}",
            reason="case_evaluation",
        ))

        data = await self._get(VA_SERVICE_HISTORY_PATH, creds)
        episodes = data.get("data", [])
        return [
            field_encryptor.encrypt_dict(
                ep.get("attributes", {}),
                user_id=user_id,
                resource_id=f"va:{creds.icn}",
            )
            for ep in episodes
        ]

    async def get_claims_status(
        self, creds: VACredentials, user_id: str,
    ) -> list[dict]:
        """Fetch the veteran's active and historical claims."""
        audit_log.record(AuditEntry(
            user_id=user_id,
            action="read",
            data_class="pii",
            field_name="claims",
            resource_id=f"va:{creds.icn}",
            reason="claims_status_check",
        ))

        path = VA_CLAIMS_PATH.format(icn=creds.icn)
        data = await self._get(path, creds)
        return data.get("data", [])

    async def get_health_conditions(
        self, creds: VACredentials, user_id: str,
    ) -> list[dict]:
        """
        Fetch the veteran's medical conditions from VA health records.
        This is FHIR R4 format from My HealtheVet.
        """
        audit_log.record(AuditEntry(
            user_id=user_id,
            action="read",
            data_class="phi",
            field_name="health_conditions",
            resource_id=f"va:{creds.icn}",
            reason="medical_evidence_review",
        ))

        data = await self._get(
            VA_HEALTH_CONDITIONS_PATH,
            creds,
            params={"patient": creds.icn},
        )

        # FHIR Bundle → extract conditions
        entries = data.get("entry", [])
        conditions = []
        for entry in entries:
            resource = entry.get("resource", {})
            conditions.append({
                "code": resource.get("code", {}).get("text", "Unknown"),
                "clinical_status": resource.get("clinicalStatus", {}).get(
                    "coding", [{}]
                )[0].get("code", "unknown"),
                "onset_date": resource.get("onsetDateTime", ""),
                "recorded_date": resource.get("recordedDate", ""),
            })
        return conditions

    async def get_medications(
        self, creds: VACredentials, user_id: str,
    ) -> list[dict]:
        """Fetch the veteran's active medications from My HealtheVet."""
        audit_log.record(AuditEntry(
            user_id=user_id,
            action="read",
            data_class="phi",
            field_name="medications",
            resource_id=f"va:{creds.icn}",
            reason="medical_evidence_review",
        ))

        data = await self._get(
            VA_HEALTH_MEDICATIONS_PATH,
            creds,
            params={"patient": creds.icn},
        )

        entries = data.get("entry", [])
        medications = []
        for entry in entries:
            resource = entry.get("resource", {})
            med = resource.get("medicationCodeableConcept", {})
            medications.append({
                "medication": med.get("text", "Unknown"),
                "status": resource.get("status", "unknown"),
                "authored_on": resource.get("authoredOn", ""),
            })
        return medications


@dataclass
class VeteranProfile:
    """
    Aggregated veteran profile assembled from VA APIs.
    All sensitive fields are encrypted by the PII Shield.
    Used to provide context for the case evaluation prompt.
    """
    user_id: str
    disability_rating: dict = field(default_factory=dict)
    service_history: list[dict] = field(default_factory=list)
    active_claims: list[dict] = field(default_factory=list)
    health_conditions: list[dict] = field(default_factory=list)
    medications: list[dict] = field(default_factory=list)

    def to_evaluation_context(self) -> str:
        """
        Format the veteran's VA data into a text block that can be
        injected into the case evaluation prompt.

        Note: Only non-PII summary data is included in the prompt.
        Specific identifiers remain encrypted.
        """
        lines = ["=== Veteran Profile (from VA.gov) ===\n"]

        if self.disability_rating:
            combined = self.disability_rating.get("combined_disability_rating", "N/A")
            lines.append(f"Combined Disability Rating: {combined}%")

        if self.service_history:
            lines.append("\nService History:")
            for ep in self.service_history:
                branch = ep.get("branch_of_service", "Unknown")
                discharge = ep.get("discharge_status", "Unknown")
                lines.append(f"  - {branch} | Discharge: {discharge}")

        if self.health_conditions:
            lines.append("\nDocumented Conditions:")
            for cond in self.health_conditions:
                status = cond.get("clinical_status", "")
                lines.append(f"  - {cond.get('code', 'Unknown')} ({status})")

        if self.active_claims:
            lines.append(f"\nActive Claims: {len(self.active_claims)}")

        return "\n".join(lines)
