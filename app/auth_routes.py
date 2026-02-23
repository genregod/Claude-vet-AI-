"""
Valor Assist — Authentication Routes

Provides the FastAPI router for all auth-related endpoints:

  POST /auth/signup              — email/password registration (fallback)
  GET  /auth/idme/login          — redirect URL for ID.me login
  POST /auth/idme/callback       — ID.me authorization code callback
  GET  /auth/va/connect          — redirect URL for VA.gov OAuth consent
  POST /auth/va/callback         — VA.gov authorization code callback
  POST /auth/refresh             — refresh an expired access token
  POST /auth/consent             — submit consent acknowledgment
  GET  /auth/consent/challenge   — get consent challenge statements
  GET  /auth/me                  — get current user profile
  POST /auth/logout              — revoke tokens and end session

Protected endpoint dependency:
  get_current_user() — extracts and validates the JWT from Authorization header
"""

from __future__ import annotations

import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, EmailStr

from app.auth import (
    AuthProvider,
    IDmeClient,
    LivenessChecker,
    TokenPair,
    UserProfile,
    UserStore,
    VerificationLevel,
    create_token_pair,
    decode_access_token,
    _hash_token,
)
from app.config import settings
from app.pii_shield import audit_log, field_encryptor, AuditEntry
from app.va_integration import VALighthouseClient, VACredentials

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ── Shared instances (initialized by server lifespan) ────────────────

user_store: UserStore | None = None
idme_client: IDmeClient | None = None
va_client: VALighthouseClient | None = None

# Temporary PKCE/state storage (in production: Redis or DynamoDB)
_auth_state_store: dict[str, dict] = {}


def init_auth_dependencies():
    """Called from server lifespan to initialize auth subsystem."""
    global user_store, idme_client, va_client
    user_store = UserStore()
    idme_client = IDmeClient()
    va_client = VALighthouseClient()
    logger.info("Auth subsystem initialized")


# ── JWT dependency for protected routes ──────────────────────────────

async def get_current_user(request: Request) -> UserProfile:
    """
    FastAPI dependency: extracts the Bearer token from the Authorization
    header, validates it, and returns the UserProfile.

    Use as: current_user: UserProfile = Depends(get_current_user)
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[7:]
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Token expired or invalid. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = user_store.get_user(payload["sub"])
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")

    # Liveness check: verify user has been active recently
    if not LivenessChecker.check_session_activity(user.last_login):
        raise HTTPException(
            status_code=403,
            detail="Session inactive. Please re-authenticate.",
        )

    return user


async def require_verified_user(
    current_user: UserProfile = Depends(get_current_user),
) -> UserProfile:
    """Dependency: requires the user to be identity-verified (LOA3+)."""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=403,
            detail=(
                "Identity verification required. Please complete ID.me "
                "verification to access this feature."
            ),
        )
    return current_user


async def require_consent(
    current_user: UserProfile = Depends(require_verified_user),
) -> UserProfile:
    """Dependency: requires consent + verification before case evaluation."""
    if not current_user.consent_given:
        raise HTTPException(
            status_code=403,
            detail="Consent required. Please acknowledge the consent statements.",
        )
    return current_user


# ── Request / Response schemas ───────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)
    first_name: str = Field("", max_length=100)
    last_name: str = Field("", max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user_id: str
    verification_level: str
    consent_given: bool


class RefreshRequest(BaseModel):
    refresh_token: str


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str


class ConsentResponse(BaseModel):
    challenge_id: str
    statements: list[dict]


class ConsentSubmission(BaseModel):
    challenge_id: str
    responses: list[dict] = Field(
        ...,
        description="List of {statement_id, confirmed: bool} objects.",
    )


class UserProfileResponse(BaseModel):
    user_id: str
    email: str
    first_name: str
    last_name: str
    verification_level: str
    veteran_status_confirmed: bool
    consent_given: bool
    va_authorized: bool


# ── Signup (fallback — email/password) ───────────────────────────────

@router.post("/signup", response_model=TokenResponse)
async def signup(request: SignupRequest):
    """
    Basic email signup for development / non-ID.me users.
    In production, all users should go through ID.me for identity proofing.
    """
    existing = user_store.get_user_by_email(request.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    # Hash password (store hash, never plaintext)
    import hashlib
    pw_hash = hashlib.sha256(
        (request.password + settings.jwt_secret_key).encode()
    ).hexdigest()

    user = user_store.create_user(
        email=request.email,
        provider=AuthProvider.OAUTH_GOOGLE,  # generic OAuth for fallback
        first_name=request.first_name,
        last_name=request.last_name,
        verification_level=VerificationLevel.LOA1,  # self-asserted only
    )

    # Encrypt and store the password hash
    field_encryptor.encrypt_field(
        pw_hash, "password", user.user_id, user.user_id,
    )

    tokens = create_token_pair(user)
    user_store.store_refresh_token(_hash_token(tokens.refresh_token), user.user_id)

    audit_log.record(AuditEntry(
        user_id=user.user_id,
        action="write",
        data_class="credential",
        field_name="signup",
        reason="account_creation",
    ))

    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        user_id=user.user_id,
        verification_level=user.verification_level.value,
        consent_given=user.consent_given,
    )


# ── ID.me OAuth2/OIDC ───────────────────────────────────────────────

@router.get("/idme/login")
async def idme_login():
    """
    Returns the ID.me authorization URL. The frontend redirects the
    user here for veteran identity verification.
    """
    auth_data = idme_client.get_authorization_url()

    # Store state + PKCE verifier for callback validation
    _auth_state_store[auth_data["state"]] = {
        "code_verifier": auth_data["code_verifier"],
        "provider": "idme",
    }

    return {
        "authorization_url": auth_data["url"],
        "state": auth_data["state"],
    }


@router.post("/idme/callback", response_model=TokenResponse)
async def idme_callback(request: OAuthCallbackRequest):
    """
    ID.me redirects back here with an authorization code.
    We exchange it for tokens and fetch the verified profile.
    """
    # Validate state (CSRF protection)
    state_data = _auth_state_store.pop(request.state, None)
    if state_data is None or state_data["provider"] != "idme":
        raise HTTPException(status_code=400, detail="Invalid or expired state.")

    # Exchange code for ID.me tokens
    idme_tokens = await idme_client.exchange_code(
        code=request.code,
        code_verifier=state_data["code_verifier"],
    )

    # Fetch verified user profile from ID.me
    idme_profile = await idme_client.get_user_info(idme_tokens["access_token"])

    # Determine verification level
    is_verified = idme_profile.get("verified", False)
    is_veteran = "veteran" in idme_profile.get("group", [])
    loa = idme_profile.get("level_of_assurance", 1)

    if is_veteran and loa >= 3:
        verification = VerificationLevel.VETERAN_CONFIRMED
    elif loa >= 3:
        verification = VerificationLevel.LOA3
    elif is_verified:
        verification = VerificationLevel.LOA1
    else:
        verification = VerificationLevel.UNVERIFIED

    # Create or update user
    user = user_store.create_user(
        email=idme_profile.get("email", ""),
        provider=AuthProvider.IDME,
        first_name=idme_profile.get("fname", ""),
        last_name=idme_profile.get("lname", ""),
        verification_level=verification,
        veteran_status_confirmed=is_veteran,
        idme_uuid=idme_profile.get("uuid"),
    )
    user.verification_level = verification
    user.veteran_status_confirmed = is_veteran
    user_store.update_user(user)

    tokens = create_token_pair(user)
    user_store.store_refresh_token(_hash_token(tokens.refresh_token), user.user_id)

    audit_log.record(AuditEntry(
        user_id=user.user_id,
        action="write",
        data_class="pii",
        field_name="idme_login",
        reason=f"identity_verification_loa{loa}",
    ))

    logger.info(
        "ID.me login: user=%s verification=%s veteran=%s",
        user.user_id, verification.value, is_veteran,
    )

    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        user_id=user.user_id,
        verification_level=verification.value,
        consent_given=user.consent_given,
    )


# ── VA.gov OAuth (medical records access) ────────────────────────────

@router.get("/va/connect")
async def va_connect(current_user: UserProfile = Depends(require_verified_user)):
    """
    Generate the VA.gov OAuth consent URL. The veteran is redirected
    to VA.gov to authorize Valor Assist to read their records.

    Requires: Identity verification (LOA3+) completed first.
    """
    state = secrets.token_urlsafe(32)
    _auth_state_store[state] = {
        "provider": "va",
        "user_id": current_user.user_id,
    }

    url = va_client.get_authorization_url(state=state)

    return {
        "authorization_url": url,
        "state": state,
        "message": (
            "You will be redirected to VA.gov to authorize access to your "
            "records. Valor Assist will only access the data you consent to."
        ),
    }


@router.post("/va/callback")
async def va_callback(request: OAuthCallbackRequest):
    """
    VA.gov redirects back here after the veteran consents.
    We exchange the code and store the VA credentials (encrypted)
    in the user's session.
    """
    state_data = _auth_state_store.pop(request.state, None)
    if state_data is None or state_data["provider"] != "va":
        raise HTTPException(status_code=400, detail="Invalid or expired state.")

    user_id = state_data["user_id"]
    user = user_store.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")

    # Exchange code for VA API tokens
    va_creds = await va_client.exchange_code(request.code)

    # Mark user as VA-authorized
    user.va_authorized = True
    user_store.update_user(user)

    # Encrypt and temporarily store VA credentials
    # (never persisted to disk — held in memory during active session only)
    encrypted_token = field_encryptor.encrypt_field(
        va_creds.va_access_token,
        "token",
        user_id=user_id,
        resource_id="va_credentials",
    )

    audit_log.record(AuditEntry(
        user_id=user_id,
        action="write",
        data_class="credential",
        field_name="va_authorization",
        reason="veteran_authorized_va_data_access",
    ))

    return {
        "status": "success",
        "message": "VA.gov access authorized. Your records are now available for case evaluation.",
        "scopes": va_creds.scopes,
    }


# ── Consent / liveness ──────────────────────────────────────────────

@router.get("/consent/challenge", response_model=ConsentResponse)
async def get_consent_challenge(
    current_user: UserProfile = Depends(require_verified_user),
):
    """
    Returns the consent challenge that the user must acknowledge
    before proceeding to case evaluation or VA data access.
    """
    challenge = LivenessChecker.generate_consent_challenge()

    # Store challenge for validation
    _auth_state_store[f"consent:{challenge['challenge_id']}"] = {
        "user_id": current_user.user_id,
        "timestamp": challenge["timestamp"],
    }

    return ConsentResponse(
        challenge_id=challenge["challenge_id"],
        statements=challenge["statements"],
    )


@router.post("/consent")
async def submit_consent(
    submission: ConsentSubmission,
    current_user: UserProfile = Depends(require_verified_user),
):
    """
    User submits their consent acknowledgment.
    All required statements must be confirmed.
    """
    state_key = f"consent:{submission.challenge_id}"
    challenge_data = _auth_state_store.pop(state_key, None)
    if challenge_data is None:
        raise HTTPException(status_code=400, detail="Invalid or expired consent challenge.")

    if challenge_data["user_id"] != current_user.user_id:
        raise HTTPException(status_code=403, detail="Consent challenge mismatch.")

    is_valid, reason = LivenessChecker.validate_consent_response(
        challenge_id=submission.challenge_id,
        responses=[r.dict() if hasattr(r, 'dict') else r for r in submission.responses],
        challenge_timestamp=challenge_data["timestamp"],
    )

    if not is_valid:
        raise HTTPException(status_code=400, detail=reason)

    # Mark consent on user profile
    current_user.consent_given = True
    user_store.update_user(current_user)

    audit_log.record(AuditEntry(
        user_id=current_user.user_id,
        action="write",
        data_class="pii",
        field_name="consent_acknowledgment",
        reason="all_statements_confirmed",
    ))

    return {
        "status": "consent_recorded",
        "message": "Thank you. You may now proceed with the case evaluation.",
    }


# ── Token management ────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """Exchange a refresh token for a new access token."""
    token_hash = _hash_token(request.refresh_token)
    user_id = user_store.validate_refresh_token(token_hash)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token.")

    user = user_store.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")

    # Rotate refresh token
    user_store.revoke_refresh_token(token_hash)
    new_tokens = create_token_pair(user)
    user_store.store_refresh_token(
        _hash_token(new_tokens.refresh_token), user.user_id,
    )

    import time
    user.last_login = time.time()
    user_store.update_user(user)

    return TokenResponse(
        access_token=new_tokens.access_token,
        refresh_token=new_tokens.refresh_token,
        token_type=new_tokens.token_type,
        expires_in=new_tokens.expires_in,
        user_id=user.user_id,
        verification_level=user.verification_level.value,
        consent_given=user.consent_given,
    )


# ── User profile ────────────────────────────────────────────────────

@router.get("/me", response_model=UserProfileResponse)
async def get_profile(current_user: UserProfile = Depends(get_current_user)):
    """Return the current user's profile."""
    return UserProfileResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        verification_level=current_user.verification_level.value,
        veteran_status_confirmed=current_user.veteran_status_confirmed,
        consent_given=current_user.consent_given,
        va_authorized=current_user.va_authorized,
    )


# ── Logout ───────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(
    request: RefreshRequest,
    current_user: UserProfile = Depends(get_current_user),
):
    """Revoke the refresh token and end the session."""
    token_hash = _hash_token(request.refresh_token)
    user_store.revoke_refresh_token(token_hash)

    audit_log.record(AuditEntry(
        user_id=current_user.user_id,
        action="delete",
        data_class="credential",
        field_name="logout",
        reason="user_initiated_logout",
    ))

    return {"status": "logged_out", "message": "Session ended."}
