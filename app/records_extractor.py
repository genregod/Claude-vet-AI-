"""
Valor Assist — Military Records Extractor

Extracts structured data from uploaded military records (DD-214, STRs,
medical records, VA rating decisions) using Claude AI to parse document
text and map extracted fields to the claim questionnaire.

Supported document types:
  - DD-214 (Certificate of Release/Discharge)
  - Service Treatment Records (STRs)
  - VA Rating Decisions
  - Medical records / Nexus letters
  - C&P Exam reports
  - Buddy/Lay statements

Flow:
  1. Upload file → extract raw text (PDF via pypdf, or plain text)
  2. Claude AI identifies document type and extracts structured fields
  3. Map extracted fields → questionnaire page answers
  4. Return field mappings for frontend auto-fill
"""

from __future__ import annotations

import json
import logging
import re
import uuid
import time
from pathlib import Path
from typing import Any

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)


# ── Supported file formats ───────────────────────────────────────────

ALLOWED_RECORD_EXTENSIONS = {".pdf", ".txt", ".md", ".jpg", ".jpeg", ".png"}
MAX_RECORD_SIZE_MB = 20  # Military records can be larger than general uploads
MAX_TEXT_LENGTH = 50_000  # Max characters to send to Claude for extraction


# ── Document types we can parse ──────────────────────────────────────

class DocumentType:
    DD214 = "dd214"
    SERVICE_TREATMENT_RECORDS = "str"
    VA_RATING_DECISION = "va_rating"
    MEDICAL_RECORDS = "medical_records"
    NEXUS_LETTER = "nexus_letter"
    CP_EXAM = "cp_exam"
    BUDDY_STATEMENT = "buddy_statement"
    UNKNOWN = "unknown"


# ── PDF Text Extraction ─────────────────────────────────────────────

def extract_text_from_pdf(file_path: Path) -> str:
    """Extract text content from a PDF file using pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(file_path))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
        full_text = "\n\n--- PAGE BREAK ---\n\n".join(pages)
        logger.info("Extracted %d characters from %d pages of %s",
                     len(full_text), len(reader.pages), file_path.name)
        return full_text
    except Exception as exc:
        logger.error("PDF extraction failed for %s: %s", file_path.name, exc)
        raise ValueError(f"Could not read PDF file: {exc}")


def extract_text_from_file(file_path: Path) -> str:
    """Extract text from a file based on its extension."""
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in {".txt", ".md"}:
        return file_path.read_text(encoding="utf-8", errors="replace")
    elif ext in {".jpg", ".jpeg", ".png"}:
        # For images, we'd need OCR — return a placeholder message
        # directing the user to upload text/PDF versions instead
        raise ValueError(
            "Image files require OCR processing. For best results, "
            "please upload a PDF or text version of your records."
        )
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# ── Claude AI Extraction Prompt ──────────────────────────────────────

RECORDS_EXTRACTION_PROMPT = """\
<role>
You are a military records analyst specializing in VA disability claims.
You extract structured data from military and medical documents to
auto-fill a veteran's disability claim questionnaire.
</role>

<document_text>
{document_text}
</document_text>

<instructions>
Analyze the uploaded document and extract ALL relevant information that
maps to a VA disability claim questionnaire. Identify the document type
and extract every field you can find.

You MUST respond with ONLY valid JSON (no markdown, no explanation).
Use this exact structure:

{{
  "document_type": "dd214|str|va_rating|medical_records|nexus_letter|cp_exam|buddy_statement|unknown",
  "document_description": "Brief description of what this document is",
  "confidence": "high|moderate|low",
  "extracted_fields": {{
    "personal_info": {{
      "first_name": "string or null",
      "last_name": "string or null",
      "date_of_birth": "YYYY-MM-DD or null",
      "ssn": "last 4 digits only or null",
      "va_file_number": "string or null",
      "address_street": "string or null",
      "address_city": "string or null",
      "address_state": "2-letter code or null",
      "address_zip": "string or null"
    }},
    "military_service": {{
      "branch": "Army|Navy|Air Force|Marine Corps|Coast Guard|Space Force|National Guard|Reserves or null",
      "rank": "pay grade / rank or null",
      "service_start_date": "YYYY-MM-DD or null",
      "service_end_date": "YYYY-MM-DD or null",
      "discharge_type": "Honorable|General (Under Honorable Conditions)|Other Than Honorable (OTH)|Bad Conduct Discharge (BCD)|Dishonorable|Uncharacterized or null",
      "mos": "MOS/Rating/AFSC code and title or null",
      "multiple_service_periods": "yes|no or null",
      "additional_service_details": "string or null"
    }},
    "service_history": {{
      "combat_deployments": "none|one|multiple or null",
      "deployment_details": "string describing deployments or null",
      "combat_decorations": "yes|no or null",
      "decorations_list": "comma-separated list or null",
      "duty_assignments": "string or null",
      "in_service_events": "string describing injuries/incidents or null"
    }},
    "disabilities": {{
      "conditions_found": ["list of medical conditions mentioned in the document"],
      "suggested_conditions": ["list of VA-recognized condition names that might match"]
    }},
    "mental_health": {{
      "mental_health_conditions": ["list of any mental health diagnoses mentioned"],
      "ptsd_stressor": "string describing PTSD stressor events or null",
      "treatment_history": "string or null"
    }},
    "medical_evidence": {{
      "has_strs": "yes|partial|no or null",
      "has_medical_records": "yes|some|no or null",
      "had_cp_exam": "yes|no or null",
      "has_nexus_letter": "yes|no or null",
      "has_buddy_statements": "yes|no or null",
      "medications": "string listing medications or null",
      "diagnoses": ["list of formal diagnoses found"],
      "treatment_providers": ["list of doctors/facilities mentioned"]
    }},
    "exposures": {{
      "burn_pit_exposure": "yes|no or null",
      "agent_orange_exposure": "yes|no or null",
      "radiation_exposure": "yes|no or null",
      "camp_lejeune": "yes|no or null",
      "other_exposures": "string or null",
      "exposure_locations": "string or null",
      "exposure_dates": "string or null"
    }}
  }},
  "raw_findings": "A brief paragraph summarizing the key findings from this document relevant to a VA claim"
}}

IMPORTANT RULES:
1. Only extract data that is EXPLICITLY stated in the document — do not infer or guess.
2. Use null for any field where information is not found.
3. For dates, convert to YYYY-MM-DD format when possible.
4. For SSN, extract ONLY the last 4 digits — never include full SSN.
5. For medical conditions, use standard VA-recognized terminology when possible.
6. If the document mentions military occupational exposures (noise, chemicals, etc.),
   note them under service_history.in_service_events.
</instructions>
"""


# ── Records Extractor Class ──────────────────────────────────────────

class RecordsExtractor:
    """
    Extracts structured questionnaire data from uploaded military records
    using Claude AI for intelligent document parsing.
    """

    def __init__(self):
        try:
            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            self._available = True
            logger.info("RecordsExtractor initialized with Anthropic client")
        except Exception as exc:
            logger.warning("RecordsExtractor: Anthropic client unavailable: %s", exc)
            self._client = None
            self._available = False

    def extract_from_file(self, file_path: Path) -> dict[str, Any]:
        """
        Extract structured data from a military record file.

        Returns:
            Dict with document_type, extracted_fields (mapped to questionnaire
            pages), confidence level, and raw_findings summary.
        """
        # Step 1: Extract raw text
        raw_text = extract_text_from_file(file_path)
        if not raw_text or len(raw_text.strip()) < 20:
            raise ValueError("Document appears to be empty or unreadable.")

        # Truncate if too long
        if len(raw_text) > MAX_TEXT_LENGTH:
            raw_text = raw_text[:MAX_TEXT_LENGTH] + "\n\n[... document truncated ...]"

        # Step 2: Send to Claude for extraction
        if self._available and self._client:
            return self._extract_with_ai(raw_text)
        else:
            return self._extract_heuristic(raw_text)

    def _extract_with_ai(self, document_text: str) -> dict[str, Any]:
        """Use Claude to intelligently extract fields from document text."""
        prompt = RECORDS_EXTRACTION_PROMPT.format(document_text=document_text)
        try:
            response = self._client.messages.create(
                model=settings.claude_model,
                system="You are a military records parsing assistant. Respond ONLY with valid JSON.",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
                temperature=0.1,
            )

            response_text = response.content[0].text.strip()

            # Try to extract JSON from the response
            # Handle potential markdown code blocks
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise ValueError("No JSON object found in response")

            # Validate required keys
            if "extracted_fields" not in result:
                result["extracted_fields"] = {}
            if "document_type" not in result:
                result["document_type"] = DocumentType.UNKNOWN
            if "confidence" not in result:
                result["confidence"] = "moderate"

            logger.info("AI extraction complete: type=%s, confidence=%s",
                        result.get("document_type"), result.get("confidence"))
            return result

        except json.JSONDecodeError as exc:
            logger.error("Failed to parse AI extraction response: %s", exc)
            return self._extract_heuristic(document_text)
        except anthropic.APIError as exc:
            logger.error("Anthropic API error during extraction: %s", exc)
            return self._extract_heuristic(document_text)
        except Exception as exc:
            logger.error("Unexpected error during AI extraction: %s", exc)
            return self._extract_heuristic(document_text)

    def _extract_heuristic(self, document_text: str) -> dict[str, Any]:
        """
        Fallback heuristic extraction when AI is unavailable.
        Uses regex patterns to find common military record fields.
        """
        text_upper = document_text.upper()
        result: dict[str, Any] = {
            "document_type": DocumentType.UNKNOWN,
            "document_description": "Document parsed with heuristic fallback",
            "confidence": "low",
            "extracted_fields": {},
            "raw_findings": "",
        }

        # Detect document type
        if "DD FORM 214" in text_upper or "DD-214" in text_upper or "CERTIFICATE OF RELEASE OR DISCHARGE" in text_upper:
            result["document_type"] = DocumentType.DD214
            result["document_description"] = "DD-214 Certificate of Release or Discharge from Active Duty"
        elif "SERVICE TREATMENT" in text_upper or "MEDICAL RECORD" in text_upper:
            result["document_type"] = DocumentType.SERVICE_TREATMENT_RECORDS
        elif "RATING DECISION" in text_upper or "DEPARTMENT OF VETERANS AFFAIRS" in text_upper:
            result["document_type"] = DocumentType.VA_RATING_DECISION
        elif "NEXUS" in text_upper and ("OPINION" in text_upper or "LETTER" in text_upper):
            result["document_type"] = DocumentType.NEXUS_LETTER
        elif "COMPENSATION AND PENSION" in text_upper or "C&P EXAM" in text_upper:
            result["document_type"] = DocumentType.CP_EXAM

        fields: dict[str, Any] = {}

        # Extract military service fields (common DD-214 patterns)
        ms: dict[str, Any] = {}

        # Branch
        for branch_name in ["ARMY", "NAVY", "AIR FORCE", "MARINE CORPS", "COAST GUARD", "SPACE FORCE"]:
            if branch_name in text_upper:
                ms["branch"] = branch_name.title()
                break

        # Discharge type
        for dtype in ["HONORABLE", "GENERAL", "OTHER THAN HONORABLE", "BAD CONDUCT", "DISHONORABLE"]:
            if dtype in text_upper:
                discharge_map = {
                    "HONORABLE": "Honorable",
                    "GENERAL": "General (Under Honorable Conditions)",
                    "OTHER THAN HONORABLE": "Other Than Honorable (OTH)",
                    "BAD CONDUCT": "Bad Conduct Discharge (BCD)",
                    "DISHONORABLE": "Dishonorable",
                }
                ms["discharge_type"] = discharge_map.get(dtype, dtype.title())
                break

        # Date patterns (MM/DD/YYYY or YYYY-MM-DD)
        date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})'
        dates_found = re.findall(date_pattern, document_text)

        # MOS pattern (e.g., "11B", "0311", "3D0X1")
        mos_pattern = r'\b(\d{1,2}[A-Z]\d?[A-Z]?\d?[A-Z]?\d?)\b'
        mos_matches = re.findall(mos_pattern, document_text)
        if mos_matches:
            ms["mos"] = mos_matches[0]

        if ms:
            fields["military_service"] = ms

        # Extract medical conditions mentioned
        conditions_found = []
        condition_keywords = [
            "PTSD", "TINNITUS", "HEARING LOSS", "SLEEP APNEA",
            "BACK PAIN", "KNEE", "SHOULDER", "DEPRESSION", "ANXIETY",
            "MIGRAINE", "HEADACHE", "HYPERTENSION", "DIABETES",
            "NEUROPATHY", "RADICULOPATHY", "TBI", "TRAUMATIC BRAIN",
            "GERD", "REFLUX", "FLAT FEET", "PLANTAR FASCIITIS",
            "CARPAL TUNNEL", "FIBROMYALGIA", "ARTHRITIS",
            "INSOMNIA", "SLEEP DISORDER", "SCIATICA",
        ]
        for keyword in condition_keywords:
            if keyword in text_upper:
                conditions_found.append(keyword.title())

        if conditions_found:
            fields["disabilities"] = {
                "conditions_found": conditions_found,
                "suggested_conditions": conditions_found,
            }

        # Exposure patterns
        exposures: dict[str, Any] = {}
        if "BURN PIT" in text_upper or "AIRBORNE HAZARD" in text_upper:
            exposures["burn_pit_exposure"] = "yes"
        if "AGENT ORANGE" in text_upper or "HERBICIDE" in text_upper:
            exposures["agent_orange_exposure"] = "yes"
        if "RADIATION" in text_upper:
            exposures["radiation_exposure"] = "yes"
        if "CAMP LEJEUNE" in text_upper:
            exposures["camp_lejeune"] = "yes"
        if exposures:
            fields["exposures"] = exposures

        result["extracted_fields"] = fields
        result["raw_findings"] = (
            f"Heuristic parsing found: document type={result['document_type']}, "
            f"conditions={conditions_found}, "
            f"branch={ms.get('branch', 'unknown')}"
        )

        return result


def map_extracted_to_questionnaire(
    extracted: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """
    Map extracted document fields to questionnaire page answer dicts.

    Returns a dict keyed by page name (personal_info, military_service, etc.)
    with only non-null field values. The frontend uses this to auto-fill
    form fields.
    """
    fields = extracted.get("extracted_fields", {})
    auto_fill: dict[str, dict[str, Any]] = {}

    for page_name, page_fields in fields.items():
        if not page_fields or not isinstance(page_fields, dict):
            continue

        clean_fields: dict[str, Any] = {}
        for key, value in page_fields.items():
            # Skip null/empty values
            if value is None or value == "" or value == []:
                continue
            clean_fields[key] = value

        if clean_fields:
            auto_fill[page_name] = clean_fields

    return auto_fill
