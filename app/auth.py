"""
Valor Assist — Authentication & Identity Verification

Implements a dual-provider auth system:

  1. ID.me OAuth2/OIDC  (preferred — veteran identity proofing, IAL2/LOA3)
     - ID.me provides free identity verification for veterans
     - Returns verified veteran status, LOA level, and unique identifier
     - Supports SAML and OIDC; we use OIDC (Authorization Code Flow + PKCE)

  2. Standard OAuth2     (fallback — Google/GitHub for dev, future extensibility)

Both flows produce a signed JWT access token for subsequent API calls.
The token is short-lived (15 min) with a refresh token (7 days).

Security model:
  - All tokens signed with HS256 using a server-side secret
  - Refresh tokens stored hashed (SHA-256) — never in plaintext
  - PKCE enforced on ID.me flow (mitigates authorization code interception)
  - Token binding to IP optional (configurable for mobile users)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

import jwt
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


# ── Enums & data structures ──────────────────────────────────────────

class AuthProvider(str, Enum):
    IDME = "id.me"
    OAUTH_GOOGLE = "google"
    OAUTH_GITHUB = "github"


class VerificationLevel(str, Enum):
    """Maps to ID.me's Identity Assurance Levels."""
    UNVERIFIED = "unverified"           # signed up, no identity proofing
    LOA1 = "loa1"                       # self-asserted identity
    LOA3 = "loa3"                       # ID.me verified (document + selfie)
    VETERAN_CONFIRMED = "veteran"       # ID.me verified + veteran status confirmed


@dataclass
class UserProfile:
    """Core user record created at signup / first login."""
    user_id: str
    email: str
    provider: AuthProvider
    verification_level: VerificationLevel = VerificationLevel.UNVERIFIED
    veteran_status_confirmed: bool = False
    idme_uuid: str | None = None        # ID.me unique identifier
    first_name: str = ""
    last_name: str = ""
    created_at: float = field(default_factory=time.time)
    last_login: float = field(default_factory=time.time)
    consent_given: bool = False         # has user agreed to ToS + data handling
    va_authorized: bool = False         # has user authorized VA data access

    @property
    def is_verified(self) -> bool:
        return self.verification_level in (
            VerificationLevel.LOA3,
            VerificationLevel.VETERAN_CONFIRMED,
        )


@dataclass
class TokenPair:
    """JWT access + refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = settings.jwt_access_token_ttl


# ── In-memory user store (swap for DynamoDB / RDS in production) ─────

class UserStore:
    """
    User persistence layer. In-memory for development.
    Production: DynamoDB with encryption at rest + GSI on email.
    """

    def __init__(self):
        self._users: dict[str, UserProfile] = {}
        self._email_index: dict[str, str] = {}  # email → user_id
        self._refresh_tokens: dict[str, str] = {}  # hash(token) → user_id
        logger.info("UserStore initialized (in-memory)")

    def create_user(
        self,
        email: str,
        provider: AuthProvider,
        **kwargs,
    ) -> UserProfile:
        existing_uid = self._email_index.get(email.lower())
        if existing_uid:
            return self._users[existing_uid]

        user = UserProfile(
            user_id=str(uuid.uuid4()),
            email=email.lower(),
            provider=provider,
            **kwargs,
        )
        self._users[user.user_id] = user
        self._email_index[email.lower()] = user.user_id
        logger.info("Created user %s via %s", user.user_id, provider.value)
        return user

    def get_user(self, user_id: str) -> UserProfile | None:
        return self._users.get(user_id)

    def get_user_by_email(self, email: str) -> UserProfile | None:
        uid = self._email_index.get(email.lower())
        return self._users.get(uid) if uid else None

    def update_user(self, user: UserProfile) -> None:
        self._users[user.user_id] = user

    def store_refresh_token(self, token_hash: str, user_id: str) -> None:
        self._refresh_tokens[token_hash] = user_id

    def validate_refresh_token(self, token_hash: str) -> str | None:
        return self._refresh_tokens.get(token_hash)

    def revoke_refresh_token(self, token_hash: str) -> None:
        self._refresh_tokens.pop(token_hash, None)


# ── JWT management ───────────────────────────────────────────────────

def _hash_token(token: str) -> str:
    """SHA-256 hash for storing refresh tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_token_pair(user: UserProfile) -> TokenPair:
    """Generate a signed JWT access token and an opaque refresh token."""
    now = int(time.time())

    access_payload = {
        "sub": user.user_id,
        "email": user.email,
        "verification_level": user.verification_level.value,
        "veteran_confirmed": user.veteran_status_confirmed,
        "consent_given": user.consent_given,
        "iat": now,
        "exp": now + settings.jwt_access_token_ttl,
        "iss": "valor-assist",
    }
    access_token = jwt.encode(
        access_payload,
        settings.jwt_secret_key,
        algorithm="HS256",
    )

    refresh_token = secrets.token_urlsafe(48)

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_ttl,
    )


def decode_access_token(token: str) -> dict | None:
    """
    Decode and validate a JWT access token.
    Returns the payload dict on success, None on failure.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"],
            issuer="valor-assist",
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Access token expired")
        return None
    except jwt.InvalidTokenError as exc:
        logger.warning("Invalid access token: %s", exc)
        return None


# ── ID.me OAuth2/OIDC integration ───────────────────────────────────

class IDmeClient:
    """
    ID.me OIDC Authorization Code Flow with PKCE.

    ID.me provides veteran identity proofing at IAL2/LOA3 level.
    Their free tier supports development and testing.

    Flow:
      1. Frontend redirects to ID.me authorize URL
      2. Veteran authenticates + verifies identity
      3. ID.me redirects back with authorization code
      4. Backend exchanges code for tokens
      5. Backend fetches user profile (including veteran status)

    Docs: https://developers.id.me/documentation
    """

    # ID.me endpoints (production — sandbox uses same domain with test accounts)
    AUTHORIZE_URL = "https://api.id.me/oauth/authorize"
    TOKEN_URL = "https://api.id.me/oauth/token"
    USERINFO_URL = "https://api.id.me/api/public/v3/userinfo"

    def __init__(self):
        self._client_id = settings.idme_client_id
        self._client_secret = settings.idme_client_secret
        self._redirect_uri = settings.idme_redirect_uri

    def get_authorization_url(self, state: str | None = None) -> dict:
        """
        Generate the ID.me authorization URL for the frontend to redirect to.

        Returns dict with:
          - url: the full authorization URL
          - state: CSRF token (store in session, verify on callback)
          - code_verifier: PKCE code verifier (store in session)
          - code_challenge: PKCE code challenge (sent to ID.me)
        """
        state = state or secrets.token_urlsafe(32)

        # PKCE: generate code_verifier and code_challenge
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = hashlib.sha256(code_verifier.encode()).digest()
        import base64
        code_challenge_b64 = (
            base64.urlsafe_b64encode(code_challenge).rstrip(b"=").decode()
        )

        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": "openid profile email military",
            # "military" scope returns veteran status attributes
            "state": state,
            "code_challenge": code_challenge_b64,
            "code_challenge_method": "S256",
        }

        url = f"{self.AUTHORIZE_URL}?" + "&".join(
            f"{k}={v}" for k, v in params.items()
        )

        return {
            "url": url,
            "state": state,
            "code_verifier": code_verifier,
            "code_challenge": code_challenge_b64,
        }

    async def exchange_code(
        self,
        code: str,
        code_verifier: str,
    ) -> dict:
        """
        Exchange authorization code for ID.me access token.

        Returns the token response dict from ID.me.
        """
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self._redirect_uri,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code_verifier": code_verifier,
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def get_user_info(self, idme_access_token: str) -> dict:
        """
        Fetch the authenticated user's profile from ID.me.

        Returns attributes including:
          - uuid: ID.me unique identifier
          - email: verified email
          - fname, lname: name
          - verified: bool (identity proofed)
          - group: "veteran" if military scope verified
          - level_of_assurance: LOA level (1 or 3)
        """
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                self.USERINFO_URL,
                headers={"Authorization": f"Bearer {idme_access_token}"},
            )
            resp.raise_for_status()
            return resp.json()


# ── Liveness / engagement verification ───────────────────────────────

class LivenessChecker:
    """
    Ensures the user is actively engaged and competent to proceed
    with claims handling authorization.

    Two-phase check:
      1. Session activity monitoring — user must interact within timeout
      2. Consent acknowledgment — explicit confirmation that the user:
         a) Is the veteran (or authorized representative)
         b) Understands what they are authorizing ValorAssist to do
         c) Is acting of their own free will and sound mind

    This is NOT a biometric liveness check (that's handled by ID.me's
    identity proofing). This is an application-level engagement check.
    """

    @staticmethod
    def check_session_activity(last_activity: float) -> bool:
        """Returns True if the user has been active within the liveness window."""
        return (time.time() - last_activity) < settings.liveness_timeout_seconds

    @staticmethod
    def generate_consent_challenge() -> dict:
        """
        Generate a consent challenge that the user must explicitly confirm
        before proceeding to case evaluation or VA data access.

        Returns a challenge payload the frontend must display and the user
        must acknowledge.
        """
        challenge_id = secrets.token_urlsafe(16)
        return {
            "challenge_id": challenge_id,
            "timestamp": time.time(),
            "statements": [
                {
                    "id": "identity_confirmation",
                    "text": (
                        "I confirm that I am the veteran named in this claim, "
                        "or I am the legally authorized representative acting "
                        "on the veteran's behalf."
                    ),
                    "required": True,
                },
                {
                    "id": "authorization_scope",
                    "text": (
                        "I authorize Valor Assist to review my claim details, "
                        "analyze applicable VA regulations on my behalf, and "
                        "prepare claim documentation. I understand that Valor "
                        "Assist does not file claims or communicate with the VA "
                        "on my behalf without my explicit, separate approval."
                    ),
                    "required": True,
                },
                {
                    "id": "competency_acknowledgment",
                    "text": (
                        "I am making this authorization voluntarily, of my own "
                        "free will, and I understand the information and actions "
                        "described above."
                    ),
                    "required": True,
                },
                {
                    "id": "data_handling_consent",
                    "text": (
                        "I understand that my personal information will be "
                        "encrypted and protected. I consent to Valor Assist "
                        "processing my claim-related data as described in the "
                        "Privacy Policy."
                    ),
                    "required": True,
                },
            ],
        }

    @staticmethod
    def validate_consent_response(
        challenge_id: str,
        responses: list[dict],
        challenge_timestamp: float,
    ) -> tuple[bool, str]:
        """
        Validate that the user acknowledged all required consent statements.

        Returns (is_valid, reason).
        """
        # Challenge must be responded to within 10 minutes
        if (time.time() - challenge_timestamp) > 600:
            return False, "Consent challenge expired. Please start again."

        required_ids = {
            "identity_confirmation",
            "authorization_scope",
            "competency_acknowledgment",
            "data_handling_consent",
        }

        confirmed_ids = {
            r["statement_id"]
            for r in responses
            if r.get("confirmed") is True
        }

        missing = required_ids - confirmed_ids
        if missing:
            return False, f"Missing required consent: {', '.join(missing)}"

        return True, "All consent statements confirmed."
