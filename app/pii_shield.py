"""
Valor Assist — PII Shield (Protection-First Framework)

This module is the central enforcement point for all PII/PHI handling.
Every piece of sensitive data — whether from the veteran directly, from
VA.gov APIs, or from uploaded documents — passes through this shield.

Threat model this protects against:
  - Database breach → all PII encrypted at rest (field-level Fernet)
  - Log leakage    → PII automatically scrubbed from log output
  - API exposure   → response sanitization before sending to frontend
  - Insider threat → access audit trail on every PII read/write
  - Session hijack → tokens bound to user, short-lived, refresh rotated

Architecture:
  ┌──────────────────────────────────────────────────────────┐
  │  PII Shield                                              │
  │                                                          │
  │  ┌────────────┐  ┌───────────────┐  ┌────────────────┐  │
  │  │ Field-Level │  │ Audit Logger  │  │ Data           │  │
  │  │ Encryption  │  │ (who accessed │  │ Classification │  │
  │  │ (Fernet)    │  │  what, when)  │  │ (PII/PHI/PFI)  │  │
  │  └────────────┘  └───────────────┘  └────────────────┘  │
  │                                                          │
  │  ┌────────────┐  ┌───────────────┐  ┌────────────────┐  │
  │  │ Log        │  │ Response      │  │ Data Retention │  │
  │  │ Scrubber   │  │ Sanitizer     │  │ Policy         │  │
  │  └────────────┘  └───────────────┘  └────────────────┘  │
  └──────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from cryptography.fernet import Fernet

from app.config import settings

logger = logging.getLogger(__name__)


# ── Data classification ──────────────────────────────────────────────

class DataClass(str, Enum):
    """
    Classification levels for sensitive data fields.
    Determines encryption requirements and audit granularity.
    """
    PUBLIC = "public"             # non-sensitive (e.g., source_type tags)
    INTERNAL = "internal"         # internal use (e.g., chunk IDs)
    PII = "pii"                   # personally identifiable (name, email, DOB)
    PHI = "phi"                   # protected health info (medical records, diagnoses)
    PFI = "pfi"                   # protected financial info (direct deposit, bank acct)
    CREDENTIAL = "credential"     # auth tokens, passwords, API keys


# Fields that must ALWAYS be encrypted at rest and scrubbed from logs
SENSITIVE_FIELD_PATTERNS: dict[str, DataClass] = {
    "ssn": DataClass.PII,
    "social_security": DataClass.PII,
    "date_of_birth": DataClass.PII,
    "dob": DataClass.PII,
    "phone": DataClass.PII,
    "address": DataClass.PII,
    "email": DataClass.PII,
    "full_name": DataClass.PII,
    "first_name": DataClass.PII,
    "last_name": DataClass.PII,
    "va_file_number": DataClass.PII,
    "claim_number": DataClass.PII,
    "diagnosis": DataClass.PHI,
    "medical_record": DataClass.PHI,
    "treatment": DataClass.PHI,
    "medication": DataClass.PHI,
    "disability": DataClass.PHI,
    "bank_account": DataClass.PFI,
    "routing_number": DataClass.PFI,
    "direct_deposit": DataClass.PFI,
    "password": DataClass.CREDENTIAL,
    "token": DataClass.CREDENTIAL,
    "api_key": DataClass.CREDENTIAL,
}


# ── Audit logger ─────────────────────────────────────────────────────

@dataclass
class AuditEntry:
    """Immutable record of a PII access event."""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    user_id: str = ""
    action: str = ""          # "read", "write", "decrypt", "export", "delete"
    data_class: str = ""      # PII, PHI, PFI
    field_name: str = ""      # which field was accessed
    resource_id: str = ""     # which record was accessed
    ip_address: str = ""
    success: bool = True
    reason: str = ""          # why access was needed


class AuditLog:
    """
    Append-only audit trail for all PII/PHI access.

    In production, this writes to a dedicated CloudWatch log group
    or a tamper-evident store (S3 with Object Lock + CloudTrail).
    """

    def __init__(self):
        self._entries: list[AuditEntry] = []
        self._audit_logger = logging.getLogger("valor_assist.audit")

    def record(self, entry: AuditEntry) -> None:
        """Record an audit event."""
        self._entries.append(entry)
        self._audit_logger.info(
            "AUDIT | %s | user=%s | action=%s | class=%s | field=%s | "
            "resource=%s | success=%s | reason=%s",
            entry.entry_id,
            entry.user_id or "system",
            entry.action,
            entry.data_class,
            entry.field_name,
            entry.resource_id,
            entry.success,
            entry.reason,
        )

    def get_entries_for_user(self, user_id: str) -> list[AuditEntry]:
        """Retrieve all audit entries for a specific user (for compliance)."""
        return [e for e in self._entries if e.user_id == user_id]


# ── Field-level encryption ───────────────────────────────────────────

class FieldEncryptor:
    """
    Encrypts individual data fields using Fernet.

    Unlike full-record encryption, field-level encryption allows us to:
      - Search on non-sensitive fields without decrypting
      - Apply different retention policies per field
      - Audit exactly which sensitive fields were accessed
    """

    def __init__(self, audit_log: AuditLog):
        self._fernet = Fernet(settings.encryption_key.encode())
        self._audit = audit_log

    def encrypt_field(
        self,
        value: str,
        field_name: str,
        user_id: str = "",
        resource_id: str = "",
    ) -> str:
        """Encrypt a single field value and log the write."""
        data_class = SENSITIVE_FIELD_PATTERNS.get(
            field_name, DataClass.INTERNAL
        )
        encrypted = self._fernet.encrypt(value.encode()).decode()

        self._audit.record(AuditEntry(
            user_id=user_id,
            action="write",
            data_class=data_class.value,
            field_name=field_name,
            resource_id=resource_id,
            reason="field_encryption",
        ))
        return encrypted

    def decrypt_field(
        self,
        encrypted_value: str,
        field_name: str,
        user_id: str = "",
        resource_id: str = "",
        reason: str = "",
    ) -> str:
        """Decrypt a single field value and log the read."""
        data_class = SENSITIVE_FIELD_PATTERNS.get(
            field_name, DataClass.INTERNAL
        )
        decrypted = self._fernet.decrypt(encrypted_value.encode()).decode()

        self._audit.record(AuditEntry(
            user_id=user_id,
            action="decrypt",
            data_class=data_class.value,
            field_name=field_name,
            resource_id=resource_id,
            reason=reason or "field_decryption",
        ))
        return decrypted

    def encrypt_dict(
        self,
        data: dict,
        user_id: str = "",
        resource_id: str = "",
    ) -> dict:
        """
        Encrypt all sensitive fields in a dict.
        Non-sensitive fields are left in plaintext.
        """
        result = {}
        for key, value in data.items():
            if key.lower() in SENSITIVE_FIELD_PATTERNS and isinstance(value, str):
                result[key] = self.encrypt_field(
                    value, key, user_id, resource_id,
                )
            else:
                result[key] = value
        return result

    def decrypt_dict(
        self,
        data: dict,
        user_id: str = "",
        resource_id: str = "",
        reason: str = "",
    ) -> dict:
        """Decrypt all sensitive fields in a dict."""
        result = {}
        for key, value in data.items():
            if key.lower() in SENSITIVE_FIELD_PATTERNS and isinstance(value, str):
                try:
                    result[key] = self.decrypt_field(
                        value, key, user_id, resource_id, reason,
                    )
                except Exception:
                    # Field wasn't encrypted (backward compat) — pass through
                    result[key] = value
            else:
                result[key] = value
        return result


# ── Log scrubber ─────────────────────────────────────────────────────

# Patterns that should NEVER appear in log output
_LOG_SCRUB_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN-SCRUBBED]"),
    (re.compile(r"\b\d{9}\b"), "[SSN-SCRUBBED]"),
    (re.compile(r"\bC-?\d{7,9}\b"), "[VAFILE-SCRUBBED]"),
    (re.compile(
        r"\b(0[1-9]|1[0-2])[/\-](0[1-9]|[12]\d|3[01])[/\-](19|20)\d{2}\b"
    ), "[DOB-SCRUBBED]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL-SCRUBBED]"),
    (re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[PHONE-SCRUBBED]"),
    # JWT tokens
    (re.compile(r"eyJ[\w-]+\.eyJ[\w-]+\.[\w-]+"), "[TOKEN-SCRUBBED]"),
    # Fernet encrypted values
    (re.compile(r"gAAAAA[\w=+/-]{40,}"), "[ENCRYPTED-SCRUBBED]"),
]


def scrub_pii_from_string(text: str) -> str:
    """Remove all PII patterns from a string before logging."""
    for pattern, replacement in _LOG_SCRUB_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class PIIScrubFilter(logging.Filter):
    """
    Logging filter that scrubs PII from all log records.

    Attach to any logger or handler to prevent PII leakage in logs:
        handler.addFilter(PIIScrubFilter())
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = scrub_pii_from_string(record.msg)
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    scrub_pii_from_string(str(a)) if isinstance(a, str) else a
                    for a in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: scrub_pii_from_string(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
        return True


# ── Response sanitizer ───────────────────────────────────────────────

def sanitize_response(data: dict, allowed_fields: set[str] | None = None) -> dict:
    """
    Strip sensitive fields from API response payloads.

    If allowed_fields is provided, only those fields are included.
    Otherwise, fields classified as CREDENTIAL or PFI are removed.
    """
    if allowed_fields:
        return {k: v for k, v in data.items() if k in allowed_fields}

    blocked_classes = {DataClass.CREDENTIAL, DataClass.PFI}
    return {
        k: v for k, v in data.items()
        if SENSITIVE_FIELD_PATTERNS.get(k.lower()) not in blocked_classes
    }


# ── Data retention policy ────────────────────────────────────────────

@dataclass
class RetentionPolicy:
    """
    Defines how long different data classes are kept.
    After expiry, data must be securely deleted.
    """
    pii_retention_days: int = 365        # 1 year (configurable per regulation)
    phi_retention_days: int = 2190       # 6 years (HIPAA minimum)
    pfi_retention_days: int = 180        # 6 months
    chat_history_days: int = 90          # 3 months
    audit_log_days: int = 2555           # 7 years (compliance standard)


# ── Singleton initialization ─────────────────────────────────────────

audit_log = AuditLog()
field_encryptor = FieldEncryptor(audit_log=audit_log)
retention_policy = RetentionPolicy()


def install_log_scrubber() -> None:
    """
    Install the PII scrub filter on the root logger.
    Call once at application startup.
    """
    root_logger = logging.getLogger()
    pii_filter = PIIScrubFilter()
    for handler in root_logger.handlers:
        handler.addFilter(pii_filter)
    root_logger.addFilter(pii_filter)
    logger.info("PII log scrubber installed on root logger")
