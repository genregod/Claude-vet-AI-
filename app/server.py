"""
Valor Assist — FastAPI Server

Exposes the RAG pipeline through HTTP endpoints:

  Public (no auth):
    GET  /health                  — liveness check
    POST /chat/session            — create a new chat session
    POST /chat                    — multi-turn Q&A (chat widget)
    POST /chat/quick-action       — pre-built quick action queries

  Auth routes (/auth/*):
    POST /auth/signup             — email/password registration
    GET  /auth/idme/login         — ID.me login redirect URL
    POST /auth/idme/callback      — ID.me authorization code callback
    GET  /auth/va/connect         — VA.gov OAuth consent redirect (requires LOA3)
    POST /auth/va/callback        — VA.gov authorization code callback
    POST /auth/consent            — consent acknowledgment
    POST /auth/refresh            — refresh access token
    GET  /auth/me                 — current user profile

  Protected (requires auth + consent):
    POST /evaluate                — case intake form evaluation
    POST /upload                  — secure document upload
    GET  /stats                   — vector store statistics
    POST /ingest                  — trigger document re-ingestion (admin)
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Any
from starlette.middleware.base import BaseHTTPMiddleware as _BHMW

from app.auth import UserProfile
from app.auth_routes import (
    get_current_user,
    init_auth_dependencies,
    require_consent,
)
from app.auth_routes import (
    router as auth_router,
)
from app.claim_routes import init_claims
from app.claim_routes import router as claims_router
from app.config import UPLOADS_DIR, settings
from app.ingest import ingest_directory, ingest_file
from app.middleware import configure_security
from app.pii_shield import install_log_scrubber
from app.prompts import QUICK_ACTION_QUERIES
from app.rag_chain import RAGChain
from app.dbq_routes import router as dbq_router
from app.va_routes import router as va_router
from app.claim_store import DynamoSessionStore, ClaimProfileStore
from app.claim_intake import extract_claim_data, get_next_intake_question
from app.cognito_auth import decode_cognito_token, is_cognito_token
from app.sessions import SessionStore
from app.vector_store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-28s  %(levelname)-7s  %(message)s",
)
logger = logging.getLogger(__name__)


# ── Application lifespan (startup / shutdown) ────────────────────────

rag_chain: RAGChain | None = None
session_store: SessionStore | None = None
dynamo_sessions: DynamoSessionStore | None = None
claim_profiles: ClaimProfileStore | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all subsystems at startup."""
    global rag_chain, session_store, dynamo_sessions, claim_profiles
    logger.info("Starting Valor Assist backend …")

    install_log_scrubber()

    store = VectorStore()
    rag_chain = RAGChain(vector_store=store)
    session_store = SessionStore()
    dynamo_sessions = DynamoSessionStore()
    claim_profiles = ClaimProfileStore()
    init_auth_dependencies()
    init_claims(vector_store=store)

    logger.info("RAG chain + session store + auth + claims initialized — ready to serve.")
    yield
    logger.info("Shutting down Valor Assist backend.")


app = FastAPI(
    title="Valor Assist",
    description=(
        "AI-powered assistant helping U.S. military veterans navigate "
        "VA disability claims, appeals, and 38 CFR regulations."
    ),
    version="0.3.0",
    lifespan=lifespan,
)

# Apply CORS, rate limiting, and security headers
configure_security(app)

# Mount authentication routes
app.include_router(auth_router)

# Mount claims questionnaire routes
app.include_router(claims_router)

# Mount DBQ assessment routes
app.include_router(dbq_router)
app.include_router(va_router)


# ── /api prefix support ─────────────────────────────────────────────
# The frontend sends all requests to /api/... (for Vite proxy in dev).
# This middleware strips the /api prefix so the same route handlers
# work for both /chat and /api/chat, etc.


class _ApiPrefixMiddleware(_BHMW):
    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/api/"):
            # Rewrite /api/chat → /chat so existing route handlers match
            scope = request.scope
            scope["path"] = request.url.path[4:]  # strip "/api"
            scope["raw_path"] = scope["path"].encode("utf-8")
        return await call_next(request)

app.add_middleware(_ApiPrefixMiddleware)


# ── Request / Response schemas ───────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="The veteran's question about VA claims or regulations.",
        json_schema_extra={"examples": ["How do I appeal a PTSD denial?"]},
    )
    session_id: str | None = Field(
        default=None,
        description="Session ID for multi-turn conversation continuity.",
    )
    source_type_filter: str | None = Field(
        default=None,
        description=(
            "Optional: restrict retrieval to a specific source type. "
            "Values: 38_CFR, M21-1_Manual, BVA_Decision, US_Code, BCMR, DRB, COVA, General."
        ),
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=10,
        description="Override default number of context chunks to retrieve.",
    )


class QuickAction(str, Enum):
    CHECK_CLAIM_STATUS = "check_claim_status"
    FILE_NEW_CLAIM = "file_new_claim"
    UPLOAD_DOCUMENTS = "upload_documents"
    LEARN_APPEALS = "learn_appeals"
    # Additional aliases the frontend sends
    LEARN_ABOUT_APPEALS = "learn_about_appeals"
    PTSD_SERVICE_CONNECTION = "ptsd_service_connection"
    CHECK_ELIGIBILITY = "check_eligibility"
    FILING_INSTRUCTIONS = "filing_instructions"


class QuickActionRequest(BaseModel):
    action: QuickAction
    session_id: str | None = None


class EvaluateRequest(BaseModel):
    service_branch: str = Field(
        ...,
        description="Military branch of service (e.g., Army, Navy, Air Force, Marines, Coast Guard).",
        json_schema_extra={"examples": ["Army"]},
    )
    current_rating: str = Field(
        ...,
        description="Current VA disability rating (e.g., '0%', '30%', '70%', 'Not yet rated').",
        json_schema_extra={"examples": ["30%"]},
    )
    primary_concerns: str = Field(
        ...,
        min_length=10,
        max_length=3000,
        description="Description of the veteran's primary claim concerns.",
        json_schema_extra={"examples": ["PTSD from combat deployment, tinnitus, and knee injury"]},
    )
    additional_details: str = Field(
        default="",
        max_length=3000,
        description="Any additional context (service dates, prior denials, etc.).",
    )


class SourceInfo(BaseModel):
    source_file: str | None
    source_type: str | None
    chunk_index: int | None
    relevance_distance: float | None


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]
    session_id: str | None
    model: str
    usage: dict


class EvaluateResponse(BaseModel):
    assessment: str
    sources: list[SourceInfo]
    model: str
    usage: dict


class SessionResponse(BaseModel):
    session_id: str
    message: str


class IngestResponse(BaseModel):
    status: str
    chunks_ingested: int
    total_documents: int


class UploadResponse(BaseModel):
    status: str
    filename: str
    chunks_ingested: int
    message: str


# ── Helper ───────────────────────────────────────────────────────────

def _require_initialized():
    if rag_chain is None or session_store is None:
        raise HTTPException(status_code=503, detail="Service not yet initialized.")


def _get_user_id(request) -> str | None:
    """Extract Cognito sub from Bearer token, or None for anonymous."""
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if token and is_cognito_token(token):
        payload = decode_cognito_token(token)
        if payload:
            return payload.get("sub")
    return None


# ── Session endpoints ────────────────────────────────────────────────

@app.post("/chat/session", response_model=SessionResponse)
async def create_session(request: Request):
    """
    Create a new chat session. Authenticated users get a DynamoDB-backed
    session (persistent across cold starts). Anonymous users get in-memory.
    """
    _require_initialized()
    user_id = _get_user_id(request)
    if user_id:
        sess = dynamo_sessions.create_session(user_id)
        return SessionResponse(session_id=sess["session_id"], message="Session created.")
    session = session_store.create_session()
    return SessionResponse(session_id=session.session_id, message="Session created.")


@app.delete("/chat/session/{session_id}", response_model=SessionResponse)
async def delete_session(session_id: str):
    """End a chat session and clear its conversation history."""
    _require_initialized()
    deleted = session_store.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found.")
    return SessionResponse(session_id=session_id, message="Session ended and history cleared.")


# ── Chat endpoint (multi-turn) ──────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request):
    """
    Primary Q&A endpoint. Authenticated users get:
      - DynamoDB-persisted conversation history (survives cold starts)
      - Automatic claim data extraction after each turn
      - Guided intake questions injected when claim fields are missing
    Anonymous users get in-memory session only.
    """
    _require_initialized()

    user_id = _get_user_id(http_request)
    conversation_history: list[dict] | None = None
    session = None

    if user_id and request.session_id:
        # Authenticated — load from DynamoDB
        conversation_history = dynamo_sessions.get_history(user_id, request.session_id)
    elif request.session_id:
        # Anonymous — load from in-memory store
        session = session_store.get_session(request.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session expired or not found.")
        conversation_history = session.get_history_for_prompt()

    try:
        result = rag_chain.ask(
            question=request.question,
            conversation_history=conversation_history,
            source_type_filter=request.source_type_filter,
            top_k=request.top_k,
        )
    except Exception as exc:
        logger.exception("Error processing chat request")
        raise HTTPException(status_code=500, detail=str(exc))

    answer = result.answer

    # ── Authenticated: persist + extract claim data ──────────────
    if user_id and request.session_id:
        dynamo_sessions.append_messages(user_id, request.session_id, request.question, answer)

        # Build full history for extraction (include this turn)
        full_history = (conversation_history or []) + [
            {"role": "user", "content": request.question},
            {"role": "assistant", "content": answer},
        ]

        # Run claim extraction asynchronously (best-effort — don't fail the request)
        try:
            extracted = extract_claim_data(full_history)
            if extracted:
                claim_profiles.upsert(user_id, extracted)
                # If intake is incomplete, append a guided follow-up question
                next_q = get_next_intake_question(extracted)
                if next_q and len(answer) < 450:
                    answer = f"{answer}\n\n{next_q}"
        except Exception as e:
            logger.warning("Claim extraction/upsert failed (non-fatal): %s", e)

    elif session:
        session.add_message("user", request.question)
        session.add_message("assistant", answer)

    return ChatResponse(
        answer=answer,
        sources=[SourceInfo(**s) for s in result.sources],
        session_id=request.session_id,
        model=result.model,
        usage=result.usage,
    )

    # Persist turns in session — handled inside chat() above
    if session:
        session.add_message("user", request.question)
        session.add_message("assistant", result.answer)

    return ChatResponse(
        answer=result.answer,
        sources=[SourceInfo(**s) for s in result.sources],
        session_id=session.session_id if session else None,
        model=result.model,
        usage=result.usage,
    )


# ── Claimant Profile + Document Upload endpoints ─────────────────────

import os as _os2
import boto3 as _boto3_s3

_S3_CLIENT = _boto3_s3.client("s3", region_name="us-east-1")
_S3_BUCKET = _os2.environ.get("S3_BUCKET", "valor-assist-documents-1773005280")
_MAX_FILES = 30
_PRESIGN_EXPIRY = 3600


class PresignRequest(BaseModel):
    filename: str
    content_type: str = "application/octet-stream"
    user_id: str


class PresignResponse(BaseModel):
    upload_url: str
    s3_key: str


class ProcessDocsRequest(BaseModel):
    user_id: str
    files: list[dict]


@app.post("/battle-buddy/upload-url", response_model=PresignResponse)
async def get_upload_url(req: PresignRequest):
    """Presigned S3 PUT URL for direct browser upload — up to 5 GB per file."""
    s3_key = f"claimant-docs/{req.user_id}/{uuid.uuid4()}_{req.filename}"
    url = _S3_CLIENT.generate_presigned_url(
        "put_object",
        Params={"Bucket": _S3_BUCKET, "Key": s3_key, "ContentType": req.content_type},
        ExpiresIn=_PRESIGN_EXPIRY,
    )
    return PresignResponse(upload_url=url, s3_key=s3_key)


@app.post("/battle-buddy/process-docs")
async def process_docs(req: ProcessDocsRequest):
    """Enqueue async doc-processing jobs (max 30 files)."""
    import json as _j, time as _t
    files = req.files[:_MAX_FILES]
    job_ids = []
    for f in files:
        job_id = str(uuid.uuid4())
        _bb_table.put_item(Item={"job_id": job_id, "status": "pending",
                                  "ttl": int(_t.time()) + 7200})
        _boto3_s3.client("lambda", region_name="us-east-1").invoke(
            FunctionName=_os2.environ.get("AWS_LAMBDA_FUNCTION_NAME", "ValorAssist-API"),
            InvocationType="Event",
            Payload=_j.dumps({"doc_process_job": {
                "job_id": job_id, "user_id": req.user_id,
                "s3_key": f["s3_key"], "filename": f["filename"],
            }}),
        )
        job_ids.append(job_id)
    return {"job_ids": job_ids, "count": len(job_ids)}


@app.get("/battle-buddy/profile/{user_id}")
async def get_claimant_profile(user_id: str):
    from app.claim_profile import get_profile
    return get_profile(user_id)


# ── Battle Buddy async endpoints (claude-opus-4-5 + extended thinking) ──

import json as _json
import os as _os
import time as _time
import boto3 as _boto3

_bb_table = _boto3.resource("dynamodb", region_name="us-east-1").Table("ValorAssist-BattleBuddyJobs")
_lambda_client = _boto3.client("lambda", region_name="us-east-1")
_FUNCTION_NAME = _os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "ValorAssist-API")


class BattleBuddyRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    conversation_history: list[dict] | None = None
    user_id: str | None = None


class BattleBuddyJobResponse(BaseModel):
    job_id: str
    status: str


@app.post("/battle-buddy/chat", response_model=BattleBuddyJobResponse)
async def battle_buddy_chat(request: BattleBuddyRequest):
    """Enqueue a Battle Buddy job and return immediately with a job_id."""
    job_id = str(uuid.uuid4())
    _bb_table.put_item(Item={
        "job_id": job_id,
        "status": "pending",
        "ttl": int(_time.time()) + 3600,
    })
    _lambda_client.invoke(
        FunctionName=_FUNCTION_NAME,
        InvocationType="Event",
        Payload=_json.dumps({"battle_buddy_job": {
            "job_id": job_id,
            "question": request.question,
            "conversation_history": request.conversation_history or [],
            "user_id": request.user_id or "",
        }}),
    )
    return BattleBuddyJobResponse(job_id=job_id, status="pending")


@app.get("/battle-buddy/result/{job_id}")
async def battle_buddy_result(job_id: str):
    """Poll for a Battle Buddy job result."""
    item = _bb_table.get_item(Key={"job_id": job_id}).get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Job not found.")
    return item


# ── Verification endpoints ────────────────────────────────────────────

class VerifyRequest(BaseModel):
    user_id: str
    conversation_history: list[dict] = []
    confirmed_fields: list[str] = []
    skipped_fields: list[str] = []
    corrections: dict = {}


class FieldUpdateRequest(BaseModel):
    field_path: str
    value: Any


@app.post("/battle-buddy/verify")
async def verify_profile_endpoint(req: VerifyRequest):
    """
    Enqueue an async verification turn.
    Returns job_id immediately; poll /battle-buddy/result/{job_id} for the response.
    """
    job_id = str(uuid.uuid4())
    _bb_table.put_item(Item={
        "job_id": job_id,
        "status": "pending",
        "ttl": int(_time.time()) + 3600,
    })
    _lambda_client.invoke(
        FunctionName=_FUNCTION_NAME,
        InvocationType="Event",
        Payload=_json.dumps({"verify_job": {
            "job_id": job_id,
            "user_id": req.user_id,
            "conversation_history": req.conversation_history,
            "confirmed_fields": req.confirmed_fields,
            "skipped_fields": req.skipped_fields,
            "corrections": req.corrections,
        }}),
    )
    return {"job_id": job_id, "status": "pending"}


@app.post("/battle-buddy/profile/{user_id}/update")
async def update_profile_field(user_id: str, req: FieldUpdateRequest):
    """Synchronously update a single profile field by dot-notation path."""
    from app.claim_profile import update_field
    try:
        profile = update_field(user_id, req.field_path, req.value)
        return {"status": "ok", "updated_field": req.field_path, "profile": profile}
    except Exception as exc:
        logger.exception("Field update failed for user %s field %s", user_id, req.field_path)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Quick actions (chat widget buttons) ──────────────────────────────

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest, http_request: Request):
    """SSE endpoint — streams Claude tokens as they arrive."""
    if rag_chain is None:
        raise HTTPException(status_code=503, detail="Service initializing.")
    user_id = getattr(http_request.state, "user_id", None)
    history: list[dict] = []
    if request.session_id:
        if user_id:
            history = dynamo_sessions.get_history(user_id, request.session_id)
        else:
            sess = session_store.get_session(request.session_id)
            if sess:
                history = sess.get("history", [])

    return StreamingResponse(
        rag_chain.ask_stream(
            question=request.question,
            conversation_history=history,
            source_type_filter=request.source_type_filter,
            top_k=request.top_k,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/chat/quick-action", response_model=ChatResponse)
async def quick_action(request: QuickActionRequest):
    """
    Handle the chat widget's quick action buttons:
      - "Check claim status"
      - "File a new claim"
      - "Upload documents"
      - "Learn about appeals"

    Each maps to a pre-built expert query that retrieves the most
    relevant legal context.
    """
    _require_initialized()

    query = QUICK_ACTION_QUERIES.get(request.action.value)
    if not query:
        raise HTTPException(status_code=400, detail="Unknown quick action.")

    session = None
    conversation_history = None
    if request.session_id:
        session = session_store.get_session(request.session_id)
        if session:
            conversation_history = session.get_history_for_prompt()

    result = rag_chain.ask(
        question=query,
        conversation_history=conversation_history,
    )

    if session:
        session.add_message("user", query)
        session.add_message("assistant", result.answer)

    return ChatResponse(
        answer=result.answer,
        sources=[SourceInfo(**s) for s in result.sources],
        session_id=session.session_id if session else None,
        model=result.model,
        usage=result.usage,
    )


# ── Case evaluation (intake form) ───────────────────────────────────

@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(
    request: EvaluateRequest,
    current_user: UserProfile = Depends(require_consent),
):
    """
    Accepts the Free Case Evaluation form data (service branch,
    current rating, primary concerns) and returns a structured
    preliminary assessment grounded in retrieved legal context.

    Requires: authentication + identity verification + consent.
    """
    _require_initialized()

    try:
        result = rag_chain.evaluate(
            service_branch=request.service_branch,
            current_rating=request.current_rating,
            primary_concerns=request.primary_concerns,
            additional_details=request.additional_details,
        )
    except Exception as exc:
        logger.exception("Error processing evaluation request")
        raise HTTPException(status_code=500, detail=str(exc))

    return EvaluateResponse(
        assessment=result.answer,
        sources=[SourceInfo(**s) for s in result.sources],
        model=result.model,
        usage=result.usage,
    )


# ── Document upload ──────────────────────────────────────────────────

ALLOWED_UPLOAD_EXTENSIONS = {".txt", ".md", ".pdf"}
MAX_UPLOAD_BYTES = settings.max_upload_size_mb * 1024 * 1024


@app.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    source_type: str = Form(default="General"),
    current_user: UserProfile = Depends(get_current_user),
):
    """
    Secure document upload endpoint. Veterans can submit supporting
    evidence files which are cleaned, chunked, and added to the
    vector store for retrieval.

    Requires: authentication.
    Accepted formats: .txt, .md
    Max size: configurable (default 10 MB)
    """
    _require_initialized()

    # Validate extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".txt", ".md"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Accepted: .txt, .md",
        )

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {settings.max_upload_size_mb} MB limit.",
        )

    # Save with a unique filename to prevent collisions
    safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    upload_path = UPLOADS_DIR / safe_name
    upload_path.write_bytes(content)

    # Ingest the uploaded file into the vector store
    try:
        chunks = ingest_file(upload_path)
        added = rag_chain._store.add_chunks(chunks)
    except Exception as exc:
        logger.exception("Error ingesting uploaded file")
        upload_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(exc))

    return UploadResponse(
        status="success",
        filename=safe_name,
        chunks_ingested=added,
        message=f"Document processed: {added} chunks added to knowledge base.",
    )


# ── Admin & utility endpoints ────────────────────────────────────────

@app.get("/health")
async def health():
    """Liveness probe."""
    return {"status": "ok", "model": settings.claude_model}


@app.get("/stats")
async def stats():
    """Return vector store and session statistics."""
    _require_initialized()
    return {
        "collection": settings.chroma_collection_name,
        "document_count": rag_chain._store.count,
        "embedding_provider": settings.embedding_provider,
        "active_sessions": session_store.active_count,
    }


@app.post("/ingest", response_model=IngestResponse)
async def ingest():
    """
    Admin endpoint: re-ingest all documents from data/raw/ into the
    vector store. Useful after adding new legal texts.
    """
    _require_initialized()
    chunks = ingest_directory()
    count = rag_chain._store.add_chunks(chunks)
    return IngestResponse(
        status="success",
        chunks_ingested=count,
        total_documents=rag_chain._store.count,
    )


# ── Serve React frontend (SPA) ───────────────────────────────────────
# IMPORTANT: This must be AFTER all API routes so the catch-all doesn't
# intercept /health, /chat, /evaluate, etc.

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if _FRONTEND_DIR.is_dir():
    # Serve static assets (JS, CSS, images) under /assets
    app.mount(
        "/assets",
        StaticFiles(directory=_FRONTEND_DIR / "assets"),
        name="frontend-assets",
    )

    @app.get("/")
    async def serve_spa_root():
        """Serve the React SPA index.html at root."""
        return FileResponse(_FRONTEND_DIR / "index.html")

    @app.get("/{full_path:path}")
    async def serve_spa_fallback(full_path: str):
        """Catch-all: serve index.html for client-side routing, or static files."""
        file_path = _FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_FRONTEND_DIR / "index.html")

    logger.info(f"Frontend SPA mounted from {_FRONTEND_DIR}")
else:
    logger.warning(
        f"Frontend build not found at {_FRONTEND_DIR} — run 'cd frontend && npm run build'"
    )


# ── Entrypoint ───────────────────────────────────────────────────────

def main():
    """Run with: python -m app.server"""
    import uvicorn
    uvicorn.run(
        "app.server:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
