"""
Valor Assist — Claim Session Management

Manages veterans' claim questionnaire sessions with:
  - Multi-page progress tracking
  - Encrypted PII storage at rest (field-level Fernet)
  - Auto-save on each page submission
  - AI-estimated disability ratings calculated in background
  - Session persistence across page reloads
  - Agent routing: Claims Agent → Supervisor Agent → Claims Assistant → FDC

Session lifecycle:
  1. Veteran clicks "Start Your Claim" → signup → create_claim_session()
  2. Each questionnaire page → save_page_answers() → triggers AI evaluation
  3. AI evaluates answers → updates estimated_rating, backpay, timeline
  4. On completion → route to assigned Claims Agent
  5. Claims Agent → Supervisor Agent review → Claims Assistant FDC prep
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cryptography.fernet import Fernet

from app.config import settings
from app.pii_shield import field_encryptor, audit_log, AuditEntry, DataClass

logger = logging.getLogger(__name__)


# ── Questionnaire page definitions ───────────────────────────────────

class ClaimPage(str, Enum):
    """Pages in the multi-step claim questionnaire."""
    SIGNUP = "signup"
    PERSONAL_INFO = "personal_info"
    MILITARY_SERVICE = "military_service"
    SERVICE_HISTORY = "service_history"
    DISABILITIES = "disabilities"
    MENTAL_HEALTH = "mental_health"
    MEDICAL_EVIDENCE = "medical_evidence"
    EXPOSURES = "exposures"
    ADDITIONAL_CLAIMS = "additional_claims"
    REVIEW = "review"


# Pages in order for progress tracking
PAGE_ORDER = list(ClaimPage)
TOTAL_PAGES = len(PAGE_ORDER)


class ClaimStatus(str, Enum):
    """Claim session workflow status."""
    INTAKE = "intake"                  # Filling out questionnaire
    AI_REVIEW = "ai_review"            # Background AI evaluating
    AGENT_ASSIGNED = "agent_assigned"   # Claims agent assigned
    SUPERVISOR_REVIEW = "supervisor_review"  # Supervisor agent reviewing
    FDC_PREP = "fdc_prep"              # Claims assistant prepping FDC
    SUBMITTED = "submitted"            # Claim submitted
    COMPLETE = "complete"


class AgentRole(str, Enum):
    """AI agent roles in the claim processing pipeline."""
    CLAIMS_AGENT = "claims_agent"
    SUPERVISOR = "supervisor"
    CLAIMS_ASSISTANT = "claims_assistant"


# ── VA-recognized claimable conditions ───────────────────────────────

# Comprehensive list of VA-recognized disabilities and claimable conditions
VA_CLAIMABLE_CONDITIONS = {
    "musculoskeletal": [
        "Back conditions (lumbar/thoracic/cervical)",
        "Knee conditions (patellofemoral syndrome, meniscus tears)",
        "Shoulder conditions (rotator cuff, impingement)",
        "Hip conditions (arthritis, labral tears)",
        "Ankle/foot conditions (plantar fasciitis, flat feet)",
        "Neck conditions (cervical strain, degenerative disc disease)",
        "Wrist/hand conditions (carpal tunnel, arthritis)",
        "Elbow conditions (lateral epicondylitis, ulnar neuropathy)",
        "Fibromyalgia",
        "Limitation of range of motion (any joint)",
        "Traumatic arthritis",
    ],
    "mental_health": [
        "PTSD (Post-Traumatic Stress Disorder)",
        "Major Depressive Disorder (MDD)",
        "Generalized Anxiety Disorder (GAD)",
        "Adjustment Disorder",
        "Bipolar Disorder",
        "Panic Disorder",
        "Obsessive-Compulsive Disorder (OCD)",
        "Military Sexual Trauma (MST)",
        "Traumatic Brain Injury (TBI)",
        "Substance Use Disorder (secondary to mental health)",
        "Insomnia/sleep disturbance (secondary to mental health)",
    ],
    "respiratory": [
        "Asthma",
        "COPD (Chronic Obstructive Pulmonary Disease)",
        "Sleep apnea (obstructive)",
        "Sinusitis/rhinitis (chronic)",
        "Pulmonary fibrosis",
        "Burn pit exposure conditions",
        "Constrictive bronchiolitis",
    ],
    "cardiovascular": [
        "Hypertension",
        "Ischemic heart disease",
        "Heart arrhythmia",
        "Peripheral vascular disease",
        "Deep vein thrombosis",
        "Varicose veins",
    ],
    "neurological": [
        "Migraines/headaches",
        "Peripheral neuropathy",
        "Radiculopathy (cervical/lumbar)",
        "Sciatica",
        "Epilepsy/seizure disorder",
        "Multiple sclerosis",
        "Parkinson's disease",
        "Vertigo/vestibular disorder",
        "Tinnitus",
        "Hearing loss (sensorineural)",
    ],
    "digestive": [
        "GERD (Gastroesophageal Reflux Disease)",
        "IBS (Irritable Bowel Syndrome)",
        "Hiatal hernia",
        "Diverticulitis",
        "Crohn's disease",
        "Ulcerative colitis",
        "Hepatitis",
        "Liver conditions",
    ],
    "skin": [
        "Eczema/dermatitis",
        "Psoriasis",
        "Acne/chloracne",
        "Skin cancer (melanoma/non-melanoma)",
        "Scarring (disfiguring)",
        "Urticaria (chronic hives)",
        "Fungal infections (chronic)",
    ],
    "endocrine": [
        "Diabetes mellitus (Type 1 or 2)",
        "Thyroid conditions (hypothyroidism/hyperthyroidism)",
        "Adrenal insufficiency",
        "Hormone disorders",
    ],
    "genitourinary": [
        "Kidney disease/renal conditions",
        "Erectile dysfunction",
        "Urinary incontinence",
        "Prostate conditions (BPH, prostatitis)",
        "Bladder conditions (interstitial cystitis)",
        "Kidney stones (recurrent)",
        "Infertility (male/female)",
    ],
    "vision": [
        "Vision impairment/loss",
        "Glaucoma",
        "Cataracts (service-connected)",
        "Macular degeneration",
        "Dry eye syndrome",
        "Diabetic retinopathy",
    ],
    "dental_oral": [
        "TMJ (temporomandibular joint disorder)",
        "Dental conditions (trauma-related)",
        "Loss of teeth (combat/service-connected)",
    ],
    "cancer": [
        "Cancer (any type, service-connected)",
        "Agent Orange-related cancers",
        "Radiation-exposure cancers",
        "Burn pit-related cancers",
    ],
    "presumptive_conditions": [
        "Agent Orange presumptives (Vietnam era)",
        "Gulf War illness/undiagnosed illness",
        "Camp Lejeune water contamination conditions",
        "PACT Act burn pit presumptives",
        "Radiation-risk presumptives (Atomic Veterans)",
    ],
    "secondary_conditions": [
        "Secondary conditions (caused by service-connected disability)",
        "Aggravation of pre-existing conditions",
        "Conditions secondary to medication side effects",
    ],
}

# Flat list for quick lookup
ALL_CLAIMABLE_CONDITIONS = [
    condition
    for category in VA_CLAIMABLE_CONDITIONS.values()
    for condition in category
]


# ── AI Estimates ─────────────────────────────────────────────────────

@dataclass
class AIEstimates:
    """AI-generated estimates updated as questionnaire progresses."""
    estimated_rating_percent: int = 0
    estimated_combined_rating: int = 0
    estimated_monthly_compensation: float = 0.0
    estimated_backpay: float = 0.0
    estimated_decision_timeline_days: int = 0
    confidence_level: str = "low"     # low, moderate, high
    individual_ratings: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "estimated_rating_percent": self.estimated_rating_percent,
            "estimated_combined_rating": self.estimated_combined_rating,
            "estimated_monthly_compensation": self.estimated_monthly_compensation,
            "estimated_backpay": self.estimated_backpay,
            "estimated_decision_timeline_days": self.estimated_decision_timeline_days,
            "confidence_level": self.confidence_level,
            "individual_ratings": self.individual_ratings,
            "notes": self.notes,
            "last_updated": self.last_updated,
        }


# ── Agent Assignment ─────────────────────────────────────────────────

@dataclass
class AgentAssignment:
    """Tracks which AI agents are handling this claim."""
    claims_agent_id: str = ""
    supervisor_id: str = ""
    claims_assistant_id: str = ""
    current_handler: AgentRole = AgentRole.CLAIMS_AGENT
    assignment_time: float = field(default_factory=time.time)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "claims_agent_id": self.claims_agent_id,
            "supervisor_id": self.supervisor_id,
            "claims_assistant_id": self.claims_assistant_id,
            "current_handler": self.current_handler.value,
            "assignment_time": self.assignment_time,
            "notes": self.notes,
        }


# ── Claim Session ────────────────────────────────────────────────────

@dataclass
class ClaimSession:
    """
    Full claim session state for a veteran going through the questionnaire.
    All PII fields are encrypted at rest via field_encryptor.
    """
    session_id: str
    user_id: str = ""
    status: ClaimStatus = ClaimStatus.INTAKE
    current_page: ClaimPage = ClaimPage.SIGNUP
    completed_pages: list[str] = field(default_factory=list)
    
    # Page answers — stored encrypted for PII fields
    answers: dict[str, dict] = field(default_factory=dict)
    
    # Uploaded file records (metadata only — files stored on disk)
    uploaded_files: list[dict] = field(default_factory=list)
    
    # AI estimates — updated as pages are completed
    ai_estimates: AIEstimates = field(default_factory=AIEstimates)
    
    # Agent assignment
    agent: AgentAssignment = field(default_factory=AgentAssignment)
    
    # Timestamps
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    
    @property
    def is_expired(self) -> bool:
        # Claim sessions have a longer TTL — 24 hours
        return (time.time() - self.last_active) > 86400
    
    @property
    def progress_percent(self) -> float:
        if not self.completed_pages:
            return 0.0
        return (len(self.completed_pages) / TOTAL_PAGES) * 100
    
    @property
    def current_page_index(self) -> int:
        try:
            return PAGE_ORDER.index(self.current_page)
        except ValueError:
            return 0
    
    def save_page(self, page: ClaimPage, answers: dict) -> None:
        """Save answers for a questionnaire page (encrypts PII fields)."""
        # Encrypt sensitive fields before storage
        encrypted_answers = field_encryptor.encrypt_dict(
            answers,
            user_id=self.user_id,
            resource_id=self.session_id,
        )
        self.answers[page.value] = encrypted_answers
        
        if page.value not in self.completed_pages:
            self.completed_pages.append(page.value)
        
        # Advance to next page
        current_idx = PAGE_ORDER.index(page)
        if current_idx + 1 < TOTAL_PAGES:
            self.current_page = PAGE_ORDER[current_idx + 1]
        
        self.last_active = time.time()
        
        audit_log.record(AuditEntry(
            user_id=self.user_id,
            action="write",
            data_class=DataClass.PII.value,
            field_name=f"claim_page_{page.value}",
            resource_id=self.session_id,
            reason="questionnaire_save",
        ))
    
    def get_page_answers(self, page: ClaimPage) -> dict:
        """Retrieve and decrypt answers for a specific page."""
        encrypted = self.answers.get(page.value, {})
        if not encrypted:
            return {}
        
        decrypted = field_encryptor.decrypt_dict(
            encrypted,
            user_id=self.user_id,
            resource_id=self.session_id,
            reason="questionnaire_recall",
        )
        return decrypted
    
    def get_all_answers_decrypted(self) -> dict:
        """Get all answers across all pages, decrypted."""
        result = {}
        for page_key, encrypted_answers in self.answers.items():
            result[page_key] = field_encryptor.decrypt_dict(
                encrypted_answers,
                user_id=self.user_id,
                resource_id=self.session_id,
                reason="full_review",
            )
        return result
    
    def add_uploaded_file(self, file_info: dict) -> None:
        """Record metadata about an uploaded file."""
        self.uploaded_files.append(file_info)
        self.last_active = time.time()

    def to_summary(self) -> dict:
        """Return a safe summary (no PII) for API responses."""
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "current_page": self.current_page.value,
            "current_page_index": self.current_page_index,
            "completed_pages": self.completed_pages,
            "progress_percent": self.progress_percent,
            "total_pages": TOTAL_PAGES,
            "ai_estimates": self.ai_estimates.to_dict(),
            "agent": self.agent.to_dict(),
            "uploaded_files_count": len(self.uploaded_files),
            "created_at": self.created_at,
            "last_active": self.last_active,
        }


# ── Claim Session Store ──────────────────────────────────────────────

class ClaimSessionStore:
    """
    In-memory store for claim sessions with encryption.
    
    Production migration: Replace _sessions dict with DynamoDB or
    PostgreSQL backend for persistence across deployments.
    """

    def __init__(self):
        self._sessions: dict[str, ClaimSession] = {}
        self._user_index: dict[str, str] = {}  # user_id → session_id
        logger.info("ClaimSessionStore initialized")

    def create_session(self, user_id: str = "") -> ClaimSession:
        """Create a new claim session."""
        session_id = str(uuid.uuid4())
        session = ClaimSession(
            session_id=session_id,
            user_id=user_id or session_id,
        )
        
        # Assign AI agents
        session.agent = AgentAssignment(
            claims_agent_id=f"agent-{uuid.uuid4().hex[:8]}",
            supervisor_id=f"supervisor-{uuid.uuid4().hex[:8]}",
            claims_assistant_id=f"assistant-{uuid.uuid4().hex[:8]}",
        )
        
        self._sessions[session_id] = session
        if user_id:
            self._user_index[user_id] = session_id
        
        self._cleanup_expired()
        logger.info("Created claim session %s for user %s", session_id, user_id or "anonymous")
        return session

    def get_session(self, session_id: str) -> ClaimSession | None:
        """Retrieve a claim session by ID."""
        session = self._sessions.get(session_id)
        if session and session.is_expired:
            logger.info("Claim session %s expired — removing", session_id)
            del self._sessions[session_id]
            return None
        return session

    def get_session_by_user(self, user_id: str) -> ClaimSession | None:
        """Retrieve claim session by user ID."""
        session_id = self._user_index.get(user_id)
        if session_id:
            return self.get_session(session_id)
        return None

    def delete_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session:
            if session.user_id in self._user_index:
                del self._user_index[session.user_id]
            del self._sessions[session_id]
            logger.info("Deleted claim session %s", session_id)
            return True
        return False

    def _cleanup_expired(self) -> None:
        expired = [sid for sid, s in self._sessions.items() if s.is_expired]
        for sid in expired:
            session = self._sessions[sid]
            if session.user_id in self._user_index:
                del self._user_index[session.user_id]
            del self._sessions[sid]
        if expired:
            logger.info("Cleaned up %d expired claim sessions", len(expired))

    @property
    def active_count(self) -> int:
        self._cleanup_expired()
        return len(self._sessions)
