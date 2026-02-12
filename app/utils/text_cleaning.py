"""
Text cleaning utilities for the Valor Assist application.

Provides PII redaction and text normalization functions used by
both the real-time API and the batch data processing pipeline.
"""

import re
import unicodedata


# PII patterns for redaction
PII_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "ssn_no_dash": re.compile(r"(?<!\d)\d{9}(?!\d)"),
    "va_file_number": re.compile(r"\b[Cc]\s*\d{7,9}\b"),
    "phone": re.compile(r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "dob": re.compile(r"\b(?:born|DOB|date of birth)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", re.IGNORECASE),
}


def redact_pii(text: str) -> str:
    """
    Redact personally identifiable information from text.

    Replaces:
        - Social Security Numbers -> [SSN REDACTED]
        - VA file numbers -> [VA FILE # REDACTED]
        - Phone numbers -> [PHONE REDACTED]
        - Email addresses -> [EMAIL REDACTED]
        - Dates of birth -> [DOB REDACTED]
    """
    text = PII_PATTERNS["ssn"].sub("[SSN REDACTED]", text)
    text = PII_PATTERNS["va_file_number"].sub("[VA FILE # REDACTED]", text)
    text = PII_PATTERNS["phone"].sub("[PHONE REDACTED]", text)
    text = PII_PATTERNS["email"].sub("[EMAIL REDACTED]", text)
    text = PII_PATTERNS["dob"].sub("[DOB REDACTED]", text)
    return text


def normalize_text(text: str) -> str:
    """
    Normalize text: Unicode normalization, whitespace cleanup,
    and encoding fixes.
    """
    # NFC normalization
    text = unicodedata.normalize("NFC", text)

    # Fix common encoding issues
    replacements = {
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": " - ",
        "\u2026": "...", "\u00a0": " ",
        "\u200b": "", "\ufeff": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # Collapse excessive whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def clean_for_embedding(text: str) -> str:
    """
    Prepare text for vector embedding.
    Redacts PII, normalizes, and removes formatting artifacts.
    """
    text = redact_pii(text)
    text = normalize_text(text)

    # Remove common artifacts
    text = re.sub(r"^(Page \d+ of \d+|[-=]{3,})\s*$", "", text, flags=re.MULTILINE)

    return text
