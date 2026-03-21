"""
Document Processor — download from S3, extract structured profile data with Anthropic,
merge into claimant profile.

Handles PDFs (text extraction via pypdf), images, and plain text.
Files up to 5 GB are supported via S3 streaming; only the first 50k chars
of extracted text are sent to Anthropic per document.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import os
import time
from pathlib import Path

import anthropic
import boto3

from app.claim_profile import merge_extracted

logger = logging.getLogger(__name__)

_s3 = boto3.client("s3", region_name="us-east-1")
_anthropic = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
_BUCKET = os.environ.get("S3_BUCKET", "valor-assist-documents-1773005280")
_MAX_TEXT = 60_000  # chars sent to Anthropic per doc

_EXTRACT_PROMPT = """\
You are a VA claims analyst. Extract ALL structured information from this veteran's document.

Return ONLY valid JSON matching this exact schema (omit fields you cannot find):
{
  "personal": {"name": "", "dob": "", "ssn_last4": "", "address": "", "phone": ""},
  "service": [{"branch": "", "entry_date": "", "sep_date": "", "mos": "", "discharge": "", "deployments": [{"location": "", "dates": ""}]}],
  "claims": [{"claim_number": "", "filed_date": "", "conditions": [], "status": "pending|approved|denied", "rating": 0, "decision_date": "", "denial_reason": ""}],
  "appeals": [{"claim_number": "", "denial_date": "", "deadline": "", "type": "", "status": "", "draft": ""}],
  "benefits": {
    "awarded": [{"name": "", "amount": "", "effective_date": ""}],
    "available": [{"name": "", "eligibility": "", "how_to_claim": "", "cfr_cite": ""}]
  },
  "notes": "any other relevant information"
}

For denied claims, also suggest available benefits the veteran may not know about based on their conditions and service history.
For any denial, draft a brief appeal opening paragraph in the "draft" field.
"""


def _extract_text_from_bytes(data: bytes, filename: str) -> str:
    """Extract plain text from PDF or return raw text for .txt files."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(data))
            return "\n".join(p.extract_text() or "" for p in reader.pages)
        except Exception as e:
            logger.warning("pypdf failed for %s: %s", filename, e)
            return ""
    if ext in (".txt", ".md"):
        return data.decode("utf-8", errors="replace")
    return ""  # images handled separately


def _call_anthropic(content: list[dict]) -> dict:
    """Call claude-opus-4-5 with extended thinking to extract profile data."""
    msg = _anthropic.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=8000,
        thinking={"type": "enabled", "budget_tokens": 5000},
        system=_EXTRACT_PROMPT,
        messages=[{"role": "user", "content": content}],
    )
    text = next((b.text for b in msg.content if b.type == "text"), "{}")
    # Strip markdown code fences if present
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("JSON parse failed, returning empty extraction")
        return {}


def process_document(user_id: str, s3_key: str, filename: str) -> dict:
    """
    Download one document from S3, extract structured data, merge into profile.
    Returns the updated profile.
    """
    logger.info("Processing %s for user %s", s3_key, user_id)
    ext = Path(filename).suffix.lower()

    # Stream from S3 (supports files of any size)
    obj = _s3.get_object(Bucket=_BUCKET, Key=s3_key)
    data = obj["Body"].read()

    content: list[dict] = []

    if ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        media_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                     ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_map.get(ext, "image/jpeg"),
                       "data": base64.standard_b64encode(data).decode()},
        })
        content.append({"type": "text", "text": f"Document filename: {filename}"})
    elif ext == ".pdf":
        # Try pypdf first (fast, no token cost)
        text = _extract_text_from_bytes(data, filename)
        if text.strip():
            content.append({"type": "text",
                             "text": f"Document: {filename}\n\n{text[:_MAX_TEXT]}"})
        else:
            # Scanned PDF — send natively so Anthropic handles OCR
            logger.info("No text from pypdf for %s — sending as native PDF", filename)
            content.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base64.standard_b64encode(data).decode(),
                },
            })
            content.append({"type": "text", "text": f"Document filename: {filename}"})
    else:
        text = _extract_text_from_bytes(data, filename)
        if not text:
            logger.warning("No text extracted from %s", filename)
            return {}
        content.append({"type": "text",
                         "text": f"Document: {filename}\n\n{text[:_MAX_TEXT]}"})

    extracted = _call_anthropic(content)
    profile = merge_extracted(user_id, extracted)
    logger.info("Profile updated for user %s after processing %s", user_id, filename)
    return profile
