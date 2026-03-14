"""
Valor Assist — DynamoDB-backed Claim & Session Persistence

Replaces in-memory SessionStore for production. All PII fields are
encrypted at rest with Fernet before writing to DynamoDB.

Tables used:
  ValorAssist-ChatSessions  (PK: userId, SK: sessionId)
  ValorAssist-Claims        (PK: claimId)
  ValorAssist-Users         (PK: userId)
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from cryptography.fernet import Fernet

from app.config import settings

logger = logging.getLogger(__name__)

_fernet = Fernet(settings.encryption_key.encode())

# ── Encryption helpers ───────────────────────────────────────────────

_PII_FIELDS = {
    "ssn", "dob", "date_of_birth", "phone", "address", "email",
    "full_name", "first_name", "last_name", "service_number",
    "medical_details", "mental_health_details", "exposure_details",
}


def _encrypt(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    try:
        return _fernet.decrypt(value.encode()).decode()
    except Exception:
        return value  # already plaintext or corrupted — return as-is


def _encrypt_pii(data: dict) -> dict:
    """Encrypt known PII fields in a dict before DynamoDB write."""
    out = {}
    for k, v in data.items():
        if k.lower() in _PII_FIELDS and isinstance(v, str) and v:
            out[k] = _encrypt(v)
        elif isinstance(v, dict):
            out[k] = _encrypt_pii(v)
        else:
            out[k] = v
    return out


def _decrypt_pii(data: dict) -> dict:
    """Decrypt PII fields after DynamoDB read."""
    out = {}
    for k, v in data.items():
        if k.lower() in _PII_FIELDS and isinstance(v, str) and v:
            out[k] = _decrypt(v)
        elif isinstance(v, dict):
            out[k] = _decrypt_pii(v)
        else:
            out[k] = v
    return out


def _to_dynamo(obj: Any) -> Any:
    """Recursively convert floats to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _to_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_dynamo(i) for i in obj]
    return obj


def _from_dynamo(obj: Any) -> Any:
    """Recursively convert Decimal back to float/int."""
    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else float(obj)
    if isinstance(obj, dict):
        return {k: _from_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_from_dynamo(i) for i in obj]
    return obj


# ── DynamoDB resource ────────────────────────────────────────────────

def _dynamo():
    return boto3.resource("dynamodb", region_name=settings.aws_region)


# ── Chat Session persistence ─────────────────────────────────────────

class DynamoSessionStore:
    """
    Persists chat sessions to ValorAssist-ChatSessions.
    Schema: PK=userId, SK=sessionId, TTL=expiresAt (epoch seconds)
    Messages stored as encrypted JSON list.
    """

    TABLE = "ValorAssist-ChatSessions"
    TTL_SECONDS = 86400 * 7  # 7 days

    def __init__(self):
        self._table = _dynamo().Table(self.TABLE)

    def create_session(self, user_id: str, metadata: dict | None = None) -> dict:
        session_id = str(uuid.uuid4())
        now = int(time.time())
        item = {
            "userId": user_id,
            "sessionId": session_id,
            "messages": [],
            "metadata": _to_dynamo(metadata or {}),
            "createdAt": now,
            "lastActive": now,
            "expiresAt": now + self.TTL_SECONDS,
        }
        self._table.put_item(Item=item)
        logger.info("Created chat session %s for user %s", session_id, user_id)
        return {"session_id": session_id, "user_id": user_id}

    def get_session(self, user_id: str, session_id: str) -> dict | None:
        resp = self._table.get_item(Key={"userId": user_id, "sessionId": session_id})
        item = resp.get("Item")
        if not item:
            return None
        if item.get("expiresAt", 0) < int(time.time()):
            logger.info("Session %s expired", session_id)
            return None
        return _from_dynamo(item)

    def append_messages(self, user_id: str, session_id: str, user_msg: str, assistant_msg: str) -> None:
        """Append a user+assistant turn. Messages stored as encrypted JSON."""
        now = int(time.time())
        turn = _encrypt(json.dumps({
            "user": user_msg,
            "assistant": assistant_msg,
            "ts": now,
        }))
        self._table.update_item(
            Key={"userId": user_id, "sessionId": session_id},
            UpdateExpression=(
                "SET #msgs = list_append(if_not_exists(#msgs, :empty), :turn), "
                "lastActive = :now, expiresAt = :exp"
            ),
            ExpressionAttributeNames={"#msgs": "messages"},
            ExpressionAttributeValues={
                ":turn": [turn],
                ":empty": [],
                ":now": now,
                ":exp": now + self.TTL_SECONDS,
            },
        )

    def get_history(self, user_id: str, session_id: str, max_turns: int = 20) -> list[dict]:
        """Return decrypted conversation history for Claude messages API."""
        session = self.get_session(user_id, session_id)
        if not session:
            return []
        messages = []
        for enc_turn in session.get("messages", [])[-max_turns:]:
            try:
                turn = json.loads(_decrypt(enc_turn))
                messages.append({"role": "user", "content": turn["user"]})
                messages.append({"role": "assistant", "content": turn["assistant"]})
            except Exception:
                continue
        return messages

    def get_latest_session(self, user_id: str) -> dict | None:
        """Get the most recent active session for a user."""
        resp = self._table.query(
            KeyConditionExpression=Key("userId").eq(user_id),
            ScanIndexForward=False,
            Limit=5,
        )
        now = int(time.time())
        for item in resp.get("Items", []):
            if item.get("expiresAt", 0) > now:
                return _from_dynamo(item)
        return None


# ── Claim Profile persistence ────────────────────────────────────────

class ClaimProfileStore:
    """
    Persists structured claim profiles to ValorAssist-Claims.
    One claim profile per veteran per condition (upserted as chat progresses).

    Schema (ValorAssist-Claims, PK: claimId):
      claimId          — uuid (stable per veteran+condition)
      userId           — Cognito sub
      claimType        — "new" | "increase" | "appeal"
      conditions       — list of claimed conditions
      serviceHistory   — branch, dates, discharge type
      serviceConnection — nexus narrative extracted from chat
      evidence         — list of evidence items mentioned
      priorRatings     — existing ratings
      chatExtracted    — raw structured data extracted by Claude
      status           — "intake" | "ready_for_review" | "submitted"
      createdAt        — epoch
      updatedAt        — epoch
    """

    TABLE = "ValorAssist-Claims"

    def __init__(self):
        self._table = _dynamo().Table(self.TABLE)

    def upsert(self, user_id: str, extracted: dict) -> str:
        """
        Upsert claim profile for a user. Uses a stable claimId derived
        from userId so the same veteran always updates the same record
        during intake (until they explicitly submit).
        """
        import hashlib
        claim_id = hashlib.sha256(f"intake:{user_id}".encode()).hexdigest()[:32]
        now = int(time.time())

        # Encrypt PII before write
        safe = _encrypt_pii(extracted)

        self._table.update_item(
            Key={"claimId": claim_id},
            UpdateExpression=(
                "SET userId = :uid, "
                "chatExtracted = :data, "
                "updatedAt = :now, "
                "#st = if_not_exists(#st, :intake), "
                "createdAt = if_not_exists(createdAt, :now)"
            ),
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":uid": user_id,
                ":data": _to_dynamo(safe),
                ":now": now,
                ":intake": "intake",
            },
        )
        logger.info("Upserted claim profile %s for user %s", claim_id, user_id)
        return claim_id

    def get_by_user(self, user_id: str) -> dict | None:
        """Retrieve the active intake claim profile for a user."""
        import hashlib
        claim_id = hashlib.sha256(f"intake:{user_id}".encode()).hexdigest()[:32]
        resp = self._table.get_item(Key={"claimId": claim_id})
        item = resp.get("Item")
        if not item:
            return None
        item = _from_dynamo(item)
        if "chatExtracted" in item:
            item["chatExtracted"] = _decrypt_pii(item["chatExtracted"])
        return item

    def get_full_history(self, user_id: str) -> list[dict]:
        """Scan all claims for a user (submitted + intake)."""
        resp = self._table.scan(
            FilterExpression=Key("userId").eq(user_id)
        )
        items = [_from_dynamo(i) for i in resp.get("Items", [])]
        for item in items:
            if "chatExtracted" in item:
                item["chatExtracted"] = _decrypt_pii(item["chatExtracted"])
        return items
