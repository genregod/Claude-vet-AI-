"""
Configuration for the data collection pipeline.
Central place for all paths, URLs, rate limits, and pipeline settings.
"""

import os
from pathlib import Path

# ──────────────────────────────────────────────
# Project root and directory structure
# ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Data directories
DATA_DIR = PROJECT_ROOT / "app" / "data"
RAW_DIR = DATA_DIR / "raw"
CLEANED_DIR = DATA_DIR / "cleaned"
TRAINING_DIR = DATA_DIR / "training"
CHROMA_DIR = DATA_DIR / "chroma_db"

# Existing data from origin/main (VA Model Training)
EXISTING_DATA_DIR = PROJECT_ROOT / "VA Model Training"

# Logging
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "data_collection.log"

# Manifest
MANIFEST_FILE = DATA_DIR / "data_manifest.json"
REPORT_FILE = DATA_DIR / "collection_report.md"

# ──────────────────────────────────────────────
# Source categories (maps to subdirectories)
# ──────────────────────────────────────────────
SOURCE_CATEGORIES = [
    "title_38_cfr",
    "title_38_usc",
    "ucmj_10_usc",
    "va_m21_1_manual",
    "vasrd_rating_schedule",
    "bva_decisions",
    "cavc_opinions",
    "federal_circuit",
    "bcmr_decisions",
    "drb_decisions",
    "dod_policy_memos",
    "va_forms",
    "vso_training",
    "claims_procedures",
    "pact_act",
    "appeals_modernization",
    "va_clinical_guidelines",
    "military_personnel_regs",
    "va_oig_reports",
    "gao_reports",
    "supplementary_legal",
]

# ──────────────────────────────────────────────
# Scraping settings
# ──────────────────────────────────────────────
DEFAULT_DELAY = 2.0            # Seconds between requests to same domain
POLITENESS_DELAY = 2.0         # Minimum delay between requests (robots.txt)
MAX_RETRIES = 5                # Maximum retry attempts per request
RETRY_BACKOFF_BASE = 2         # Exponential backoff base (seconds)
REQUEST_TIMEOUT = 60           # HTTP request timeout (seconds)
MAX_CONCURRENT_REQUESTS = 3    # Async concurrency limit per domain

# ──────────────────────────────────────────────
# Source URLs
# ──────────────────────────────────────────────

ECFR_API_BASE = "https://www.ecfr.gov/api/versioner/v1"
ECFR_TITLE_38 = f"{ECFR_API_BASE}/full/current/title-38.xml"
ECFR_STRUCTURE = f"{ECFR_API_BASE}/structure/current/title-38.json"

GOVINFO_BASE = "https://www.govinfo.gov"
GOVINFO_CFR_BULK = f"{GOVINFO_BASE}/bulkdata/CFR/"
GOVINFO_USCODE_BASE = f"{GOVINFO_BASE}/content/pkg"

USCODE_DOWNLOAD = "https://uscode.house.gov/download/download.shtml"
USCODE_XML_BASE = "https://uscode.house.gov/download/releasepoints/us/pl"

BVA_SEARCH = "https://www.index.va.gov/search/va/bva.jsp"
BVA_SEARCH_API = "https://www.index.va.gov/search/va/bva_search.jsp"

CAVC_OPINIONS = "https://www.uscourts.cavc.gov/opinions.php"
CAVC_DECISIONS_BASE = "https://www.uscourts.cavc.gov"

FEDERAL_CIRCUIT_OPINIONS = "https://cafc.uscourts.gov/home/case-information/opinions-orders/"

VA_FORMS_BASE = "https://www.va.gov/find-forms/"
VA_FORMS_API = "https://api.va.gov/services/va_forms/v0/forms"

VA_CLINICAL_GUIDELINES = "https://www.healthquality.va.gov/guidelines/"

VA_OIG_BASE = "https://www.va.gov/oig/"
GAO_BASE = "https://www.gao.gov/"

# M21-1 Manual
VA_M21_1_BASE = "https://www.knowva.ebenefits.va.gov/system/templates/selfservice/va_ssnew/help/customer/locale/en-US/portal/554400000001018/"

# BCMR/DRB URLs
ABCMR_URL = "https://arba.army.pentagon.mil/abcmr-overview.html"
BCNR_URL = "https://www.secnav.navy.mil/mra/bcnr/"
AFBCMR_URL = "https://www.afpc.af.mil/Board-for-Correction-of-Military-Records/"
ARMY_DRB_URL = "https://arba.army.pentagon.mil/adrb-overview.html"
NAVY_DRB_URL = "https://www.secnav.navy.mil/mra/bcnr/Pages/ndrb.aspx"
AF_DRB_URL = "https://www.afpc.af.mil/Discharge-Review-Board/"

# DoD Policy Memos (search terms — actual URLs resolved at runtime)
DOD_MEMO_KEYWORDS = {
    "hagel_memo_2014": "Hagel supplemental guidance PTSD discharge review 2014",
    "carson_memo_2014": "Carson memo PTSD liberal consideration 2014",
    "kurta_memo_2017": "Kurta memo liberal consideration discharge upgrade mental health TBI MST 2017",
    "wilkie_memo_2018": "Wilkie memo BCMR liberal consideration standards 2018",
    "dod_equity_clemency_2017": "DoD guidance equity injustice clemency discharge review August 2017",
}

# ──────────────────────────────────────────────
# Fine-tuning dataset settings
# ──────────────────────────────────────────────
TRAINING_FORMATS = ["instruction_response", "multi_turn_conversation"]
MIN_RESPONSE_LENGTH = 100       # Minimum characters for a training response
MAX_RESPONSE_LENGTH = 4000      # Maximum characters for a training response
MIN_INSTRUCTION_LENGTH = 20     # Minimum characters for a training instruction

# ──────────────────────────────────────────────
# ChromaDB settings
# ──────────────────────────────────────────────
CHROMA_COLLECTION_NAME = "valor_assist_knowledge"
CHUNK_SIZE = 1000               # Characters per chunk for embedding
CHUNK_OVERLAP = 200             # Overlap between chunks

# ──────────────────────────────────────────────
# PII patterns for redaction
# ──────────────────────────────────────────────
PII_PATTERNS = {
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "ssn_no_dash": r"\b\d{9}\b",
    "va_file_number": r"\b[Cc]\s*\d{7,9}\b",
    "phone": r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "dob_pattern": r"\b(?:born|DOB|date of birth)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
}

# ──────────────────────────────────────────────
# Ensure directories exist
# ──────────────────────────────────────────────
def ensure_directories():
    """Create all required directories if they don't exist."""
    for category in SOURCE_CATEGORIES:
        (RAW_DIR / category).mkdir(parents=True, exist_ok=True)
        (CLEANED_DIR / category).mkdir(parents=True, exist_ok=True)
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
