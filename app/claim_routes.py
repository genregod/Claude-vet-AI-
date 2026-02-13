"""
Valor Assist — Claim Questionnaire API Routes

Endpoints for the multi-page claim questionnaire flow:

  POST /claims/session           — Create a new claim session
  GET  /claims/session/{id}      — Get session status + progress
  POST /claims/session/{id}/page — Save a questionnaire page
  GET  /claims/session/{id}/page/{page} — Retrieve saved answers
  GET  /claims/session/{id}/estimates   — Get current AI estimates
  POST /claims/session/{id}/evaluate    — Trigger full AI evaluation
  POST /claims/session/{id}/submit      — Submit completed claim
  GET  /claims/conditions        — List all claimable conditions
  POST /claims/session/{id}/upload — Upload military records for auto-fill
  DELETE /claims/session/{id}    — Delete a claim session
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from app.claim_session import (
    ClaimSession, ClaimSessionStore, ClaimPage, ClaimStatus,
    VA_CLAIMABLE_CONDITIONS, ALL_CLAIMABLE_CONDITIONS,
    PAGE_ORDER, TOTAL_PAGES,
)
from app.claims_evaluator import ClaimsEvaluator
from app.config import settings, UPLOADS_DIR
from app.records_extractor import (
    RecordsExtractor,
    map_extracted_to_questionnaire,
    ALLOWED_RECORD_EXTENSIONS,
    MAX_RECORD_SIZE_MB,
)
from app.vector_store import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/claims", tags=["claims"])

# ── Module-level singletons (initialized by server.py lifespan) ──────

_claim_store: ClaimSessionStore | None = None
_evaluator: ClaimsEvaluator | None = None
_extractor: RecordsExtractor | None = None


def init_claims(vector_store: VectorStore | None = None):
    """Called during app lifespan startup."""
    global _claim_store, _evaluator, _extractor
    _claim_store = ClaimSessionStore()
    _evaluator = ClaimsEvaluator(vector_store=vector_store)
    _extractor = RecordsExtractor()
    logger.info("Claims subsystem initialized (with records extractor)")


def _require_claims():
    if _claim_store is None or _evaluator is None:
        raise HTTPException(status_code=503, detail="Claims subsystem not initialized.")


# ── Request / Response schemas ───────────────────────────────────────

class CreateClaimSessionRequest(BaseModel):
    """Signup data to create a new claim session."""
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    first_name: str = Field(default="", max_length=100)
    last_name: str = Field(default="", max_length=100)


class CreateClaimSessionResponse(BaseModel):
    session_id: str
    message: str
    current_page: str
    total_pages: int


class SavePageRequest(BaseModel):
    """Answers for a single questionnaire page."""
    page: str = Field(..., description="Page identifier (e.g., 'personal_info')")
    answers: dict[str, Any] = Field(..., description="Page answers as key-value pairs")


class SavePageResponse(BaseModel):
    session_id: str
    page_saved: str
    next_page: str | None
    progress_percent: float
    ai_estimates: dict
    completed_pages: list[str]


class ClaimSessionStatus(BaseModel):
    session_id: str
    status: str
    current_page: str
    current_page_index: int
    completed_pages: list[str]
    progress_percent: float
    total_pages: int
    ai_estimates: dict
    agent: dict
    uploaded_files_count: int = 0
    created_at: float
    last_active: float


class AIEstimatesResponse(BaseModel):
    estimated_rating_percent: int
    estimated_combined_rating: int
    estimated_monthly_compensation: float
    estimated_backpay: float
    estimated_decision_timeline_days: int
    confidence_level: str
    individual_ratings: list[dict]
    notes: list[str]
    last_updated: float


class ConditionsResponse(BaseModel):
    categories: dict[str, list[str]]
    all_conditions: list[str]
    total_count: int


class SubmitClaimResponse(BaseModel):
    session_id: str
    status: str
    fdc_package: dict
    supervisor_review: dict
    message: str


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/session", response_model=CreateClaimSessionResponse)
async def create_claim_session(request: CreateClaimSessionRequest):
    """
    Create a new claim session after veteran signup.
    Returns session_id for all subsequent questionnaire interactions.
    """
    _require_claims()
    
    # Create session with user identifier
    session = _claim_store.create_session(user_id=request.email)
    
    # Save signup info as the first page
    session.save_page(ClaimPage.SIGNUP, {
        "email": request.email,
        "first_name": request.first_name,
        "last_name": request.last_name,
    })
    
    return CreateClaimSessionResponse(
        session_id=session.session_id,
        message="Claim session created. Begin filling out the questionnaire.",
        current_page=session.current_page.value,
        total_pages=TOTAL_PAGES,
    )


@router.get("/session/{session_id}", response_model=ClaimSessionStatus)
async def get_claim_session(session_id: str):
    """Get current session status, progress, and AI estimates."""
    _require_claims()
    
    session = _claim_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Claim session not found or expired.")
    
    summary = session.to_summary()
    return ClaimSessionStatus(**summary)


@router.post("/session/{session_id}/page", response_model=SavePageResponse)
async def save_page_answers(session_id: str, request: SavePageRequest):
    """
    Save answers for a questionnaire page.
    Triggers background AI evaluation after each save.
    Returns updated progress and AI estimates.
    """
    _require_claims()
    
    session = _claim_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Claim session not found or expired.")
    
    # Validate page name
    try:
        page = ClaimPage(request.page)
    except ValueError:
        valid_pages = [p.value for p in ClaimPage]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid page '{request.page}'. Valid: {valid_pages}",
        )
    
    # Save page answers (auto-encrypts PII)
    session.save_page(page, request.answers)
    
    # Trigger background AI evaluation
    try:
        estimates = _evaluator.evaluate_claim(session)
        session.ai_estimates = estimates
    except Exception as exc:
        logger.warning("AI evaluation failed for session %s: %s", session_id, exc)
    
    # Determine next page
    next_page = None
    page_idx = PAGE_ORDER.index(page)
    if page_idx + 1 < TOTAL_PAGES:
        next_page = PAGE_ORDER[page_idx + 1].value
    
    return SavePageResponse(
        session_id=session_id,
        page_saved=page.value,
        next_page=next_page,
        progress_percent=session.progress_percent,
        ai_estimates=session.ai_estimates.to_dict(),
        completed_pages=session.completed_pages,
    )


@router.get("/session/{session_id}/page/{page_name}")
async def get_page_answers(session_id: str, page_name: str):
    """Retrieve previously saved answers for a specific page."""
    _require_claims()
    
    session = _claim_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Claim session not found or expired.")
    
    try:
        page = ClaimPage(page_name)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid page '{page_name}'.")
    
    answers = session.get_page_answers(page)
    return {
        "session_id": session_id,
        "page": page_name,
        "answers": answers,
        "is_completed": page_name in session.completed_pages,
    }


@router.get("/session/{session_id}/estimates", response_model=AIEstimatesResponse)
async def get_ai_estimates(session_id: str):
    """Get current AI-generated estimates for this claim."""
    _require_claims()
    
    session = _claim_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Claim session not found or expired.")
    
    return AIEstimatesResponse(**session.ai_estimates.to_dict())


@router.post("/session/{session_id}/evaluate")
async def trigger_evaluation(session_id: str):
    """Manually trigger a full AI evaluation of current answers."""
    _require_claims()
    
    session = _claim_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Claim session not found or expired.")
    
    estimates = _evaluator.evaluate_claim(session)
    session.ai_estimates = estimates
    
    return {
        "session_id": session_id,
        "estimates": estimates.to_dict(),
        "message": "Full AI evaluation completed.",
    }


@router.post("/session/{session_id}/submit", response_model=SubmitClaimResponse)
async def submit_claim(session_id: str):
    """
    Submit completed questionnaire through the agent pipeline:
    Claims Agent → Supervisor → Claims Assistant → FDC Package
    """
    _require_claims()
    
    session = _claim_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Claim session not found or expired.")
    
    # Check minimum pages completed
    required_pages = ["personal_info", "military_service", "disabilities"]
    missing = [p for p in required_pages if p not in session.completed_pages]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Required pages not completed: {missing}",
        )
    
    # Step 1: Claims Agent analysis (already done via evaluate_claim)
    session.status = ClaimStatus.AGENT_ASSIGNED
    
    # Step 2: Supervisor review
    supervisor_review = _evaluator.route_to_supervisor(session)
    
    # Step 3: Claims Assistant FDC preparation
    fdc_package = _evaluator.prepare_fdc(session)
    
    session.status = ClaimStatus.SUBMITTED
    
    return SubmitClaimResponse(
        session_id=session_id,
        status="submitted",
        fdc_package=fdc_package,
        supervisor_review=supervisor_review,
        message=(
            "Your claim has been processed through our AI agent pipeline. "
            "A Claims Agent has analyzed your case, a Supervisor has validated "
            "the assessment, and a Claims Assistant has prepared your Fully "
            "Developed Claim (FDC) package."
        ),
    )


@router.get("/conditions", response_model=ConditionsResponse)
async def get_claimable_conditions():
    """Return all VA-recognized claimable conditions organized by category."""
    return ConditionsResponse(
        categories=VA_CLAIMABLE_CONDITIONS,
        all_conditions=ALL_CLAIMABLE_CONDITIONS,
        total_count=len(ALL_CLAIMABLE_CONDITIONS),
    )


# ── Military Records Upload & Auto-Fill ──────────────────────────────

@router.post("/session/{session_id}/upload")
async def upload_military_records(
    session_id: str,
    file: UploadFile = File(...),
):
    """
    Upload a military record (DD-214, STRs, medical records, etc.)
    for AI-powered extraction and questionnaire auto-fill.

    Accepts: .pdf, .txt, .md
    Max size: 20 MB

    Returns extracted fields mapped to questionnaire pages so the
    frontend can auto-populate form fields.
    """
    _require_claims()
    if _extractor is None:
        raise HTTPException(status_code=503, detail="Records extractor not available.")

    session = _claim_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Claim session not found or expired.")

    # Validate file extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_RECORD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{ext}'. "
                f"Accepted: {', '.join(sorted(ALLOWED_RECORD_EXTENSIONS))}"
            ),
        )

    # Read and validate size
    content = await file.read()
    max_bytes = MAX_RECORD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {MAX_RECORD_SIZE_MB} MB limit.",
        )

    # Save to uploads directory with unique prefix
    safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    upload_path = UPLOADS_DIR / safe_name
    upload_path.write_bytes(content)

    try:
        # Extract structured data from the document
        extraction_result = _extractor.extract_from_file(upload_path)

        # Map extracted fields to questionnaire page answers
        auto_fill_pages = map_extracted_to_questionnaire(extraction_result)

        # Track the uploaded file in the session
        session.add_uploaded_file({
            "filename": file.filename,
            "saved_as": safe_name,
            "size_bytes": len(content),
            "document_type": extraction_result.get("document_type", "unknown"),
            "confidence": extraction_result.get("confidence", "low"),
            "pages_affected": list(auto_fill_pages.keys()),
        })

        # Auto-merge extracted answers into session (don't overwrite existing answers)
        merged_pages = []
        for page_name, extracted_answers in auto_fill_pages.items():
            try:
                page_enum = ClaimPage(page_name)
            except ValueError:
                continue

            # Get existing answers for this page
            existing = session.get_page_answers(page_enum)

            # Merge: extracted values fill in blanks, don't overwrite user input
            merged = {**extracted_answers, **existing}
            session.save_page(page_enum, merged)
            merged_pages.append(page_name)

        # Trigger AI evaluation with the new data
        try:
            estimates = _evaluator.evaluate_claim(session)
            session.ai_estimates = estimates
        except Exception as exc:
            logger.warning("AI evaluation after upload failed: %s", exc)

        return {
            "session_id": session_id,
            "filename": file.filename,
            "document_type": extraction_result.get("document_type", "unknown"),
            "document_description": extraction_result.get("document_description", ""),
            "confidence": extraction_result.get("confidence", "low"),
            "auto_fill_pages": auto_fill_pages,
            "pages_affected": list(auto_fill_pages.keys()),
            "merged_pages": merged_pages,
            "raw_findings": extraction_result.get("raw_findings", ""),
            "ai_estimates": session.ai_estimates.to_dict(),
            "message": (
                f"Document analyzed successfully. "
                f"Auto-filled {len(merged_pages)} questionnaire page(s): "
                f"{', '.join(merged_pages)}."
            ),
        }

    except ValueError as exc:
        # Clean up on failure
        upload_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        upload_path.unlink(missing_ok=True)
        logger.exception("Error extracting records from %s", file.filename)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {exc}",
        )


@router.get("/session/{session_id}/uploads")
async def get_uploaded_files(session_id: str):
    """List all files uploaded for this claim session."""
    _require_claims()

    session = _claim_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Claim session not found or expired.")

    return {
        "session_id": session_id,
        "files": session.uploaded_files,
        "total": len(session.uploaded_files),
    }


@router.delete("/session/{session_id}")
async def delete_claim_session(session_id: str):
    """Delete a claim session and all stored data."""
    _require_claims()
    
    deleted = _claim_store.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Claim session not found.")
    
    return {
        "session_id": session_id,
        "message": "Claim session and all associated data have been securely deleted.",
    }
