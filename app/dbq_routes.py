"""
Valor Assist — DBQ Assessment Routes

POST /dbq/conditions  — list supported conditions + questions
POST /dbq/evaluate    — RAG-grounded rating evaluation, stored in DynamoDB

Auth: requires Cognito Bearer token (sub used as userId).
RAG:  Voyage AI → OpenSearch k-NN → DynamoDB DocumentMetadata → Claude.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import anthropic
import boto3
import voyageai
from fastapi import APIRouter, Depends, HTTPException, Request
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from pydantic import BaseModel

from app.cognito_auth import decode_cognito_token, is_cognito_token
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dbq", tags=["DBQ Assessment"])

# ── Condition catalogue ──────────────────────────────────────────────

DBQ_CONDITIONS: dict[str, dict] = {
    "ptsd": {
        "label": "PTSD",
        "cfr_query": "38 CFR Part 4 PTSD rating criteria diagnostic code 9411 occupational social impairment",
        "questions": [
            {"id": "impairment", "text": "How would you describe your occupational and social impairment?", "type": "select",
             "options": ["No impairment", "Mild/transient symptoms", "Occasional decrease in work efficiency",
                         "Reduced reliability and productivity", "Considerable level of impairment",
                         "Total occupational and social impairment"]},
            {"id": "symptoms", "text": "Which symptoms do you experience? (select all that apply)", "type": "multiselect",
             "options": ["Depressed mood", "Anxiety", "Panic attacks", "Chronic sleep impairment",
                         "Mild memory loss", "Flattened affect", "Suicidal ideation",
                         "Impaired impulse control", "Neglect of personal hygiene"]},
            {"id": "frequency", "text": "How often do symptoms occur?", "type": "select",
             "options": ["Rarely", "Occasionally", "Frequently", "Constantly"]},
        ],
    },
    "tinnitus": {
        "label": "Tinnitus",
        "cfr_query": "38 CFR Part 4 tinnitus rating criteria diagnostic code 6260",
        "questions": [
            {"id": "affected_ears", "text": "Which ear(s) are affected?", "type": "select",
             "options": ["Right ear only", "Left ear only", "Both ears"]},
            {"id": "frequency", "text": "How often do you experience tinnitus?", "type": "select",
             "options": ["Occasional", "Frequent", "Constant"]},
            {"id": "impact", "text": "How does tinnitus impact your daily life?", "type": "textarea"},
        ],
    },
    "lumbar_spine": {
        "label": "Lumbar Spine (Back)",
        "cfr_query": "38 CFR Part 4 lumbar spine rating criteria diagnostic code 5235 5237 range of motion forward flexion",
        "questions": [
            {"id": "forward_flexion", "text": "What is your forward flexion range of motion?", "type": "select",
             "options": ["Greater than 90°", "60° to 90°", "30° to 60°", "Less than 30°"]},
            {"id": "painful_motion", "text": "Do you have pain on motion?", "type": "select",
             "options": ["No", "Yes — mild", "Yes — moderate", "Yes — severe"]},
            {"id": "incapacitating_episodes", "text": "Incapacitating episodes per year requiring bed rest?", "type": "select",
             "options": ["None", "Less than 2 weeks total", "2–4 weeks total", "4–6 weeks total", "More than 6 weeks total"]},
            {"id": "neurological", "text": "Neurological symptoms (numbness, weakness, radiculopathy)?", "type": "select",
             "options": ["None", "Mild", "Moderate", "Severe"]},
        ],
    },
    "knee": {
        "label": "Knee Condition",
        "cfr_query": "38 CFR Part 4 knee rating criteria diagnostic code 5257 5260 5261 limitation flexion extension instability",
        "questions": [
            {"id": "flexion", "text": "Knee flexion range of motion?", "type": "select",
             "options": ["Greater than 60°", "45° to 60°", "30° to 45°", "Less than 30°"]},
            {"id": "extension_loss", "text": "Limitation of extension?", "type": "select",
             "options": ["No limitation", "Limited to 5°", "Limited to 10°", "Limited to 15°", "Limited beyond 15°"]},
            {"id": "instability", "text": "Knee instability?", "type": "select",
             "options": ["None", "Mild (0–25%)", "Moderate (26–50%)", "Severe (51–75%)", "Total (76–100%)"]},
        ],
    },
    "tbi": {
        "label": "Traumatic Brain Injury (TBI)",
        "cfr_query": "38 CFR Part 4 TBI traumatic brain injury rating criteria diagnostic code 8045 cognitive impairment",
        "questions": [
            {"id": "cognitive", "text": "Cognitive impairment level?", "type": "select",
             "options": ["None", "Mild — subjective symptoms only", "Moderate — objective findings",
                         "Severe — severe cognitive impairment"]},
            {"id": "neurobehavioral", "text": "Neurobehavioral effects?", "type": "select",
             "options": ["None", "One or two symptoms, mild", "Three or more symptoms, or one/two moderate",
                         "One or more severe symptoms"]},
            {"id": "communication", "text": "Communication difficulties?", "type": "select",
             "options": ["None", "Occasional difficulty", "Frequent difficulty", "Unable to communicate effectively"]},
        ],
    },
}


# ── OpenSearch + DynamoDB helpers ────────────────────────────────────

def _os_client() -> OpenSearch:
    endpoint = settings.opensearch_endpoint.replace("https://", "")
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, settings.aws_region, "aoss")
    return OpenSearch(
        hosts=[{"host": endpoint, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )


def _retrieve_cfr_context(cfr_query: str, k: int = 5) -> str:
    """Embed cfr_query, search OpenSearch, fetch text from DynamoDB."""
    voyage = voyageai.Client(api_key=settings.voyage_api_key)
    embedding = voyage.embed([cfr_query], model="voyage-large-2").embeddings[0]

    os = _os_client()
    index = getattr(settings, "opensearch_index", "document-embeddings")
    resp = os.search(
        index=index,
        body={"size": k, "query": {"knn": {"embedding": {"vector": embedding, "k": k}}}},
    )
    hits = resp["hits"]["hits"]
    if not hits:
        return ""

    dynamo = boto3.resource("dynamodb", region_name=settings.aws_region)
    table = dynamo.Table("ValorAssist-DocumentMetadata")
    chunks: list[str] = []
    for hit in hits:
        doc_id = hit["_source"].get("documentId")
        if doc_id:
            item = table.get_item(Key={"documentId": doc_id}).get("Item")
            if item:
                chunks.append(item["text"])
    return "\n\n---\n\n".join(chunks)


def _get_user_id(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if token and is_cognito_token(token):
        payload = decode_cognito_token(token)
        if payload:
            return payload.get("sub", "anonymous")
    return "anonymous"


# ── Schemas ──────────────────────────────────────────────────────────

class EvaluateRequest(BaseModel):
    condition: str
    answers: dict[str, Any]


class EvaluateResponse(BaseModel):
    claim_id: str
    condition: str
    estimated_rating: int
    rationale: str
    supporting_factors: list[str]
    limiting_factors: list[str]
    cfr_citations: list[str]


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/conditions")
def list_conditions():
    return [{"id": k, "label": v["label"], "questions": v["questions"]} for k, v in DBQ_CONDITIONS.items()]


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate(body: EvaluateRequest, request: Request):
    condition = DBQ_CONDITIONS.get(body.condition)
    if not condition:
        raise HTTPException(status_code=400, detail=f"Unknown condition: {body.condition}")

    # 1. RAG retrieval — 38 CFR criteria for this condition
    cfr_context = _retrieve_cfr_context(condition["cfr_query"])
    if not cfr_context:
        cfr_context = "(No 38 CFR text retrieved — evaluation based on general knowledge only)"
        logger.warning("No CFR context retrieved for condition: %s", body.condition)

    # 2. Build Claude prompt
    answers_text = "\n".join(f"- {k}: {v}" for k, v in body.answers.items())
    prompt = f"""You are evaluating a VA disability claim for {condition['label']}.

RETRIEVED 38 CFR RATING CRITERIA (base your evaluation ONLY on this text):
{cfr_context}

VETERAN'S REPORTED SYMPTOMS AND ANSWERS:
{answers_text}

Based SOLELY on the retrieved 38 CFR criteria above, provide a structured evaluation.
Respond with valid JSON only, no other text:
{{
  "estimated_rating": <integer: 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, or 100>,
  "rationale": "<one paragraph citing specific CFR criteria>",
  "supporting_factors": ["<factor>"],
  "limiting_factors": ["<factor>"],
  "cfr_citations": ["<e.g. 38 CFR § 4.130, DC 9411>"]
}}"""

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise HTTPException(status_code=502, detail="Failed to parse evaluation response")
        result = json.loads(match.group())

    # 3. Store in DynamoDB
    claim_id = str(uuid.uuid4())
    user_id = _get_user_id(request)
    dynamo = boto3.resource("dynamodb", region_name=settings.aws_region)
    dynamo.Table("ValorAssist-Claims").put_item(Item={
        "claimId": claim_id,
        "userId": user_id,
        "condition": body.condition,
        "answers": body.answers,
        "estimatedRating": result.get("estimated_rating", 0),
        "rationale": result.get("rationale", ""),
        "supportingFactors": result.get("supporting_factors", []),
        "limitingFactors": result.get("limiting_factors", []),
        "cfrCitations": result.get("cfr_citations", []),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    })

    return EvaluateResponse(
        claim_id=claim_id,
        condition=body.condition,
        estimated_rating=result.get("estimated_rating", 0),
        rationale=result.get("rationale", ""),
        supporting_factors=result.get("supporting_factors", []),
        limiting_factors=result.get("limiting_factors", []),
        cfr_citations=result.get("cfr_citations", []),
    )
