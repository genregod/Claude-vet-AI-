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

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from app.auth import UserProfile
from app.auth_routes import (
    router as auth_router,
    get_current_user,
    require_consent,
    init_auth_dependencies,
)
from app.config import settings, UPLOADS_DIR
from app.ingest import ingest_directory, ingest_file
from app.middleware import configure_security
from app.pii_shield import install_log_scrubber
from app.prompts import QUICK_ACTION_QUERIES
from app.rag_chain import RAGChain
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all subsystems at startup."""
    global rag_chain, session_store
    logger.info("Starting Valor Assist backend …")

    # Install PII log scrubber FIRST — protects all subsequent log output
    install_log_scrubber()

    store = VectorStore()
    rag_chain = RAGChain(vector_store=store)
    session_store = SessionStore()
    init_auth_dependencies()

    logger.info("RAG chain + session store + auth initialized — ready to serve.")
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


# ── Session endpoints ────────────────────────────────────────────────

@app.post("/chat/session", response_model=SessionResponse)
async def create_session():
    """
    Create a new chat session. Returns a session_id that the frontend
    should include in subsequent /chat requests for conversation continuity.
    """
    _require_initialized()
    session = session_store.create_session()
    return SessionResponse(
        session_id=session.session_id,
        message="Session created. Include this session_id in /chat requests.",
    )


@app.delete("/chat/session/{session_id}", response_model=SessionResponse)
async def delete_session(session_id: str):
    """End a chat session and clear its conversation history."""
    _require_initialized()
    deleted = session_store.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found.")
    return SessionResponse(
        session_id=session_id,
        message="Session ended and history cleared.",
    )


# ── Chat endpoint (multi-turn) ──────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Primary Q&A endpoint for the chat widget.

    If a session_id is provided, conversation history is maintained
    across turns. The system retrieves fresh legal context for each
    question and passes it alongside the conversation history to Claude.
    """
    _require_initialized()

    # Resolve session (optional — works without one too)
    session = None
    conversation_history = None
    if request.session_id:
        session = session_store.get_session(request.session_id)
        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Session expired or not found. Create a new session.",
            )
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

    # Persist turns in session
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


# ── Quick actions (chat widget buttons) ──────────────────────────────

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
