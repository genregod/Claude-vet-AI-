"""
Valor Assist — Claim Intake Extractor

After each chat turn, runs a lightweight Claude call to extract structured
claim-relevant data from the conversation. Extracted data is upserted to
ValorAssist-Claims via ClaimProfileStore.

Extracted fields:
  - claimType        (new | increase | appeal | unknown)
  - conditions       (list of claimed conditions)
  - serviceHistory   (branch, dates, discharge)
  - serviceConnection (nexus narrative)
  - evidence         (medical records, buddy statements, nexus letters, etc.)
  - priorRatings     (existing VA ratings mentioned)
  - appealInfo       (decision date, docket, lane if appeal)
  - urgencyFlags     (homeless, financial hardship, terminal illness, etc.)
"""

from __future__ import annotations

import json
import logging
import re

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


_EXTRACT_PROMPT = """\
You are a VA claims data extractor. Given a conversation between a veteran and an AI assistant,
extract any claim-relevant information mentioned. Return ONLY valid JSON — no other text.

Extract these fields (use null if not mentioned):
{
  "claimType": "new" | "increase" | "appeal" | null,
  "conditions": ["<condition name>"],
  "serviceHistory": {
    "branch": null,
    "entryDate": null,
    "separationDate": null,
    "dischargeType": null,
    "deployments": []
  },
  "serviceConnection": "<brief nexus narrative or null>",
  "evidence": {
    "medicalRecords": true | false | null,
    "nexusLetter": true | false | null,
    "buddyStatements": true | false | null,
    "privateTreatment": true | false | null,
    "other": []
  },
  "priorRatings": [{"condition": "<name>", "rating": <int or null>}],
  "appealInfo": {
    "priorDecisionDate": null,
    "docketNumber": null,
    "lane": null
  },
  "urgencyFlags": [],
  "incomplete": ["<field names still needed>"]
}

Only extract what is explicitly stated. Do not infer or assume.
"""


def extract_claim_data(conversation_history: list[dict]) -> dict | None:
    """
    Run extraction on the last N turns of conversation.
    Returns structured dict or None if nothing claim-relevant found.
    """
    if not conversation_history:
        return None

    # Only send last 10 turns to keep token cost low
    recent = conversation_history[-20:]
    convo_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in recent
    )

    try:
        msg = _get_client().messages.create(
            model="claude-haiku-4-20250514",  # fast + cheap for extraction
            max_tokens=512,
            messages=[
                {"role": "user", "content": f"{_EXTRACT_PROMPT}\n\nCONVERSATION:\n{convo_text}"}
            ],
        )
        raw = msg.content[0].text.strip()
        # Extract JSON from response
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group())

        # Only persist if something meaningful was extracted
        has_data = (
            data.get("conditions") or
            data.get("claimType") or
            (data.get("serviceHistory") or {}).get("branch") or
            data.get("serviceConnection")
        )
        return data if has_data else None

    except Exception as e:
        logger.warning("Claim extraction failed: %s", e)
        return None


# ── Guided intake questions ──────────────────────────────────────────
# Val uses these to prompt the veteran when claim data is incomplete.

INTAKE_QUESTIONS = {
    "claimType": "Are you filing a new claim, requesting an increase on an existing rating, or appealing a decision?",
    "conditions": "What conditions or injuries are you claiming? List all of them.",
    "serviceHistory.branch": "What branch of service were you in, and what were your service dates?",
    "serviceHistory.dischargeType": "What was your discharge type (honorable, general, etc.)?",
    "serviceConnection": "Can you describe how your condition is connected to your military service?",
    "evidence.medicalRecords": "Do you have VA or private medical records documenting your condition?",
    "evidence.nexusLetter": "Do you have a nexus letter from a doctor linking your condition to service?",
    "priorRatings": "Do you currently have any VA disability ratings? If so, what are they?",
}


def get_next_intake_question(extracted: dict | None) -> str | None:
    """
    Given what's been extracted so far, return the next question Val
    should ask to complete the intake profile. Returns None when complete.
    """
    if not extracted:
        return INTAKE_QUESTIONS["claimType"]

    checks = [
        ("claimType", extracted.get("claimType")),
        ("conditions", extracted.get("conditions")),
        ("serviceHistory.branch", (extracted.get("serviceHistory") or {}).get("branch")),
        ("serviceHistory.dischargeType", (extracted.get("serviceHistory") or {}).get("dischargeType")),
        ("serviceConnection", extracted.get("serviceConnection")),
        ("evidence.medicalRecords", (extracted.get("evidence") or {}).get("medicalRecords")),
        ("priorRatings", extracted.get("priorRatings") is not None),
    ]

    for field, value in checks:
        if not value:
            return INTAKE_QUESTIONS.get(field)

    return None  # intake complete
