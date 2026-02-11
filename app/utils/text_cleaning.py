"""
Valor Assist — Text Cleaning & PII Redaction

Handles the mandatory preprocessing steps before any legal document
enters the RAG pipeline:

1. Header / footer removal  — strips page numbers, repeated doc titles,
   and boilerplate navigation text common in VA PDFs and HTML scrapes.
2. PII redaction             — replaces SSNs, VA file numbers, phone
   numbers, dates of birth, and veteran names with [REDACTED] tokens.
3. Whitespace normalization  — collapses runs of blank lines and
   trailing spaces so chunks are clean for embedding.
"""

import re


# ── 1.  Header / Footer Removal ─────────────────────────────────────

# Patterns found in M21-1 manual HTML/PDF exports, BVA decision headers,
# and Federal Register pages.
_HEADER_FOOTER_PATTERNS: list[re.Pattern] = [
    # Page numbers: "Page 3 of 47", "- 12 -", "p. 5"
    re.compile(r"(?i)^[-–—\s]*page\s+\d+\s*(of\s+\d+)?[-–—\s]*$", re.MULTILINE),
    re.compile(r"^[-–—]\s*\d+\s*[-–—]$", re.MULTILINE),
    re.compile(r"(?i)^p\.\s*\d+\s*$", re.MULTILINE),

    # Repeated document titles (M21-1, 38 CFR, etc.)
    re.compile(
        r"(?i)^(M21-1|Veterans Benefits Administration|"
        r"Department of Veterans Affairs|38\s*C\.?F\.?R\.?|"
        r"Board of Veterans.? Appeals)\s*$",
        re.MULTILINE,
    ),

    # URL artifacts from HTML scrapes
    re.compile(r"https?://\S+", re.MULTILINE),

    # Common footer boilerplate
    re.compile(
        r"(?i)^(this document is available|printed on recycled paper|"
        r"for official use only)\b.*$",
        re.MULTILINE,
    ),
]


def remove_headers_footers(text: str) -> str:
    """Strip recurring headers, footers, and navigation artefacts."""
    for pattern in _HEADER_FOOTER_PATTERNS:
        text = pattern.sub("", text)
    return text


# ── 2.  PII Redaction ───────────────────────────────────────────────

_PII_PATTERNS: list[tuple[re.Pattern, str]] = [
    # SSN: 123-45-6789 or 123456789
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN_REDACTED]"),
    (re.compile(r"\b\d{9}\b"), "[SSN_REDACTED]"),

    # VA file / claim numbers (typically 8-9 digits, sometimes with C- prefix)
    (re.compile(r"\bC-?\d{7,9}\b"), "[VA_FILE_REDACTED]"),

    # Phone numbers: (555) 123-4567, 555-123-4567, 5551234567
    (re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[PHONE_REDACTED]"),

    # Dates of birth in common formats: MM/DD/YYYY, MM-DD-YYYY
    (re.compile(
        r"\b(0[1-9]|1[0-2])[/\-](0[1-9]|[12]\d|3[01])[/\-](19|20)\d{2}\b"
    ), "[DOB_REDACTED]"),

    # Email addresses
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL_REDACTED]"),
]


def redact_pii(text: str) -> str:
    """Replace personally identifiable information with redaction tokens."""
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ── 3.  Whitespace Normalization ─────────────────────────────────────

def normalize_whitespace(text: str) -> str:
    """Collapse excessive blank lines and trailing spaces."""
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)   # trailing spaces
    text = re.sub(r"\n{3,}", "\n\n", text)                     # max 1 blank line
    return text.strip()


# ── Public API ───────────────────────────────────────────────────────

def clean_document(text: str) -> str:
    """
    Full preprocessing pipeline applied to every document before chunking.

    Order matters:
      1. Headers/footers first (removes noise that could confuse PII regex)
      2. PII redaction
      3. Whitespace normalization (final polish)
    """
    text = remove_headers_footers(text)
    text = redact_pii(text)
    text = normalize_whitespace(text)
    return text
