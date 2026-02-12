"""
Data Cleaning Pipeline

Processes all collected raw data through:
1. Format normalization (PDF, DOCX, HTML → clean plaintext)
2. Legal text processing (preserve hierarchy, cross-references, citations)
3. PII redaction (SSNs, VA file numbers, DOBs, names, etc.)
4. Deduplication (hash-based)
5. Quality validation (min word counts, citation validation, completeness)
"""

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scripts.data_collection.config import (
    RAW_DIR,
    CLEANED_DIR,
    SOURCE_CATEGORIES,
    PII_PATTERNS,
    ensure_directories,
)
from scripts.data_collection.logger import get_logger

logger = get_logger("pipeline.clean")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FORMAT NORMALIZATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def extract_text_from_pdf(filepath: Path) -> Optional[str]:
    """Extract text from a PDF file using pdfplumber (with PyMuPDF fallback)."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        if text_parts:
            return "\n\n".join(text_parts)
    except ImportError:
        logger.warning("pdfplumber not installed, trying PyMuPDF")
    except Exception as e:
        logger.warning(f"pdfplumber failed for {filepath}: {e}")

    # Fallback: PyMuPDF
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(filepath))
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        if text_parts:
            return "\n\n".join(text_parts)
    except ImportError:
        logger.warning("PyMuPDF not installed, cannot extract PDF text")
    except Exception as e:
        logger.warning(f"PyMuPDF failed for {filepath}: {e}")

    return None


def extract_text_from_docx(filepath: Path) -> Optional[str]:
    """Extract text from a Word document."""
    try:
        from docx import Document
        doc = Document(str(filepath))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except ImportError:
        logger.warning("python-docx not installed")
    except Exception as e:
        logger.warning(f"DOCX extraction failed for {filepath}: {e}")
    return None


def extract_text_from_html(filepath: Path) -> Optional[str]:
    """Extract clean text from an HTML file."""
    try:
        from bs4 import BeautifulSoup
        html = filepath.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")

        # Remove non-content elements
        for tag in soup(["script", "style", "nav", "header", "footer",
                         "aside", "form", "button", "iframe"]):
            tag.decompose()

        # Extract structured text preserving hierarchy
        lines = []
        for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6",
                                       "p", "li", "td", "th", "pre", "blockquote"]):
            text = element.get_text(separator=" ", strip=True)
            if not text:
                continue

            tag = element.name
            if tag in ("h1", "h2"):
                lines.extend(["", "=" * 60, text, "=" * 60, ""])
            elif tag in ("h3", "h4"):
                lines.extend(["", text, "-" * min(len(text), 60), ""])
            elif tag in ("h5", "h6"):
                lines.extend(["", text, ""])
            elif tag == "li":
                lines.append(f"  - {text}")
            elif tag in ("td", "th"):
                lines.append(f"  | {text}")
            elif tag == "pre":
                lines.extend(["", text, ""])
            elif tag == "blockquote":
                lines.append(f"  > {text}")
            else:
                lines.extend([text, ""])

        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"HTML extraction failed for {filepath}: {e}")
    return None


def extract_text_from_xml(filepath: Path) -> Optional[str]:
    """Extract text content from XML files (eCFR, GovInfo, etc.)."""
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(str(filepath))
        root = tree.getroot()

        # Remove namespace prefixes for easier processing
        text_parts = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                text_parts.append(elem.text.strip())
            if elem.tail and elem.tail.strip():
                text_parts.append(elem.tail.strip())

        return "\n".join(text_parts)
    except Exception as e:
        logger.warning(f"XML extraction failed for {filepath}: {e}")
    return None


def normalize_to_text(filepath: Path) -> Optional[str]:
    """Convert any supported file format to plain text."""
    suffix = filepath.suffix.lower()

    if suffix == ".txt":
        try:
            return filepath.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.error(f"Failed to read text file {filepath}: {e}")
            return None
    elif suffix == ".pdf":
        return extract_text_from_pdf(filepath)
    elif suffix == ".docx":
        return extract_text_from_docx(filepath)
    elif suffix in (".html", ".htm"):
        return extract_text_from_html(filepath)
    elif suffix == ".xml":
        return extract_text_from_xml(filepath)
    elif suffix in (".json", ".jsonl"):
        # JSON/JSONL files are metadata or structured data — skip text extraction
        return None
    elif suffix == ".md":
        try:
            return filepath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None
    else:
        logger.debug(f"Unsupported format for text extraction: {suffix}")
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LEGAL TEXT PROCESSING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def normalize_unicode(text: str) -> str:
    """Normalize Unicode characters and fix encoding issues."""
    # NFC normalization
    text = unicodedata.normalize("NFC", text)

    # Replace common problematic characters
    replacements = {
        "\u2018": "'",   # Left single quote
        "\u2019": "'",   # Right single quote
        "\u201c": '"',   # Left double quote
        "\u201d": '"',   # Right double quote
        "\u2013": "-",   # En dash
        "\u2014": " — ", # Em dash (keep with spaces for readability)
        "\u2026": "...", # Ellipsis
        "\u00a0": " ",   # Non-breaking space
        "\u200b": "",    # Zero-width space
        "\ufeff": "",    # BOM
        "\u00ad": "",    # Soft hyphen
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def clean_whitespace(text: str) -> str:
    """Normalize whitespace while preserving paragraph structure."""
    # Replace tabs with spaces
    text = text.replace("\t", "    ")

    # Collapse multiple spaces (but not newlines)
    text = re.sub(r"[^\S\n]+", " ", text)

    # Collapse 3+ consecutive newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip trailing whitespace per line
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()


def preserve_legal_citations(text: str) -> str:
    """
    Ensure legal citations are properly formatted and preserved.
    This normalizes citation formats without breaking them.
    """
    # Normalize CFR citations: "38 C.F.R. § 3.304(f)" → "38 CFR 3.304(f)"
    text = re.sub(r'38\s*C\.?F\.?R\.?\s*§?\s*', '38 CFR ', text)

    # Normalize USC citations
    text = re.sub(r'38\s*U\.?S\.?C\.?\s*§?\s*', '38 USC ', text)
    text = re.sub(r'10\s*U\.?S\.?C\.?\s*§?\s*', '10 USC ', text)

    # Normalize case citations — preserve "v." format
    text = re.sub(r'\bvs?\.?\b', 'v.', text)

    # Preserve section symbol
    text = text.replace("§§", "§§").replace("§", "§")

    return text


def remove_boilerplate(text: str) -> str:
    """Remove navigation elements, headers/footers, page numbers."""
    # Remove common navigation/boilerplate patterns
    boilerplate_patterns = [
        r'(?i)skip to (?:main )?content',
        r'(?i)back to top',
        r'(?i)(?:previous|next) (?:page|section)',
        r'(?i)table of contents',
        r'(?i)print this page',
        r'(?i)share this page',
        r'(?i)last (?:updated|modified|reviewed):?\s*\d+[/-]\d+[/-]\d+',
        r'(?i)page \d+ of \d+',
        r'^\s*\d+\s*$',  # Standalone page numbers
        r'(?i)cookie\s*(?:policy|notice|consent)',
        r'(?i)privacy\s*(?:policy|notice)',
    ]

    for pattern in boilerplate_patterns:
        text = re.sub(pattern, '', text, flags=re.MULTILINE)

    return text


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PII REDACTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def redact_pii(text: str) -> str:
    """
    Aggressively redact personally identifiable information.
    Replaces SSNs, VA file numbers, DOBs, phone numbers, emails,
    and veteran names in case decisions.
    """
    # SSN patterns
    text = re.sub(PII_PATTERNS["ssn"], "[SSN REDACTED]", text)
    text = re.sub(PII_PATTERNS["va_file_number"], "[VA FILE # REDACTED]", text)
    text = re.sub(PII_PATTERNS["phone"], "[PHONE REDACTED]", text)
    text = re.sub(PII_PATTERNS["email"], "[EMAIL REDACTED]", text)
    text = re.sub(PII_PATTERNS["dob_pattern"], "[DOB REDACTED]", text, flags=re.IGNORECASE)

    # Redact SSN-like 9-digit sequences that appear near PII context
    text = re.sub(
        r'(?i)(?:social security|SSN|ss#|ss #)\s*[:=]?\s*\d[\d\s-]{7,10}\d',
        "[SSN REDACTED]",
        text
    )

    # Redact addresses (basic pattern — street addresses)
    text = re.sub(
        r'\d+\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Circle|Cir)\.?,?\s*(?:Apt|Suite|Unit|#)?\s*\d*',
        "[ADDRESS REDACTED]",
        text,
        flags=re.IGNORECASE,
    )

    return text


def redact_veteran_names_in_decisions(text: str) -> str:
    """
    Redact veteran names in BVA/CAVC decisions.
    Keeps attorney and judge names. Replaces veteran identifiers.
    """
    # Common patterns in BVA decisions identifying the veteran
    patterns = [
        # "The veteran, JOHN DOE," or "The appellant, JOHN DOE,"
        (r'(?i)(the (?:veteran|appellant|claimant)),\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', r'\1, [VETERAN]'),
        # Names after "Name:" or "Veteran:" labels
        (r'(?i)((?:veteran|appellant|claimant)\s*(?:name)?:)\s*[A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+', r'\1 [VETERAN]'),
    ]

    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)

    return text


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DEDUPLICATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class Deduplicator:
    """Hash-based deduplication tracker."""

    def __init__(self):
        self.seen_hashes: dict[str, str] = {}  # hash → first filepath
        self.duplicates: list[tuple[str, str]] = []  # (duplicate, original)

    def is_duplicate(self, text: str, filepath: str) -> bool:
        """Check if text content is a duplicate of previously seen content."""
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        if content_hash in self.seen_hashes:
            original = self.seen_hashes[content_hash]
            self.duplicates.append((filepath, original))
            return True

        self.seen_hashes[content_hash] = filepath
        return False

    def get_stats(self) -> dict:
        return {
            "unique_documents": len(self.seen_hashes),
            "duplicates_found": len(self.duplicates),
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# QUALITY VALIDATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


# Minimum word counts by document type
MIN_WORD_COUNTS = {
    "cfr_part": 500,
    "usc_chapter": 200,
    "bva_decision": 200,
    "cavc_opinion": 200,
    "m21_1_section": 100,
    "reference": 50,
    "form_info": 50,
    "default": 30,
}


def validate_quality(text: str, doc_type: str = "default") -> tuple[bool, list[str]]:
    """
    Validate document quality.

    Returns:
        (is_valid, list_of_issues)
    """
    issues = []
    word_count = len(text.split())

    min_words = MIN_WORD_COUNTS.get(doc_type, MIN_WORD_COUNTS["default"])
    if word_count < min_words:
        issues.append(f"Below minimum word count: {word_count} < {min_words}")

    # Check for mostly garbage text
    alpha_ratio = sum(c.isalpha() for c in text) / max(len(text), 1)
    if alpha_ratio < 0.3:
        issues.append(f"Low alphabetic ratio: {alpha_ratio:.2f}")

    # Check for encoding artifacts
    if "Ã" in text or "â€" in text or "Â" in text:
        issues.append("Possible encoding artifacts detected")

    is_valid = len(issues) == 0
    return is_valid, issues


def validate_legal_citations(text: str) -> list[str]:
    """Check for proper legal citation formatting."""
    issues = []

    # Check for common citation patterns
    cfr_refs = re.findall(r'38 CFR \d+\.\d+', text)
    usc_refs = re.findall(r'38 USC \d+', text)

    # Not an issue per se, but useful metadata
    if not cfr_refs and not usc_refs:
        issues.append("No legal citations found (may be expected for some document types)")

    return issues


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN CLEANING PIPELINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def clean_text(text: str, doc_type: str = "default",
               is_case_decision: bool = False) -> str:
    """
    Apply the full cleaning pipeline to a text document.

    Args:
        text: Raw text content.
        doc_type: Document type for quality validation.
        is_case_decision: If True, apply veteran name redaction.

    Returns:
        Cleaned text.
    """
    # Step 1: Unicode normalization
    text = normalize_unicode(text)

    # Step 2: Remove boilerplate
    text = remove_boilerplate(text)

    # Step 3: Preserve legal citations
    text = preserve_legal_citations(text)

    # Step 4: PII redaction
    text = redact_pii(text)
    if is_case_decision:
        text = redact_veteran_names_in_decisions(text)

    # Step 5: Whitespace normalization
    text = clean_whitespace(text)

    return text


def process_category(category: str, deduplicator: Deduplicator) -> dict:
    """Process all files in a single source category."""
    raw_dir = RAW_DIR / category
    cleaned_dir = CLEANED_DIR / category
    cleaned_dir.mkdir(parents=True, exist_ok=True)

    stats = {
        "category": category,
        "files_processed": 0,
        "files_cleaned": 0,
        "files_skipped": 0,
        "duplicates": 0,
        "quality_failures": 0,
        "total_words": 0,
    }

    if not raw_dir.exists():
        logger.debug(f"No raw directory for {category}")
        return stats

    # Determine if this category contains case decisions (for PII redaction)
    decision_categories = {"bva_decisions", "cavc_opinions", "federal_circuit", "bcmr_decisions"}
    is_decision = category in decision_categories

    for filepath in sorted(raw_dir.iterdir()):
        # Skip metadata sidecar files
        if filepath.name.endswith(".meta.json"):
            continue

        stats["files_processed"] += 1

        # Extract text
        text = normalize_to_text(filepath)
        if text is None:
            stats["files_skipped"] += 1
            continue

        # Clean
        doc_type = _infer_doc_type(category, filepath.name)
        cleaned = clean_text(text, doc_type=doc_type, is_case_decision=is_decision)

        # Validate quality
        is_valid, issues = validate_quality(cleaned, doc_type)
        if not is_valid:
            logger.debug(f"Quality issues for {filepath.name}: {issues}")
            stats["quality_failures"] += 1
            # Still save but note issues

        # Check for duplicates
        if deduplicator.is_duplicate(cleaned, str(filepath)):
            logger.debug(f"Duplicate: {filepath.name}")
            stats["duplicates"] += 1
            continue

        # Save cleaned file
        output_name = filepath.stem + ".txt"
        output_path = cleaned_dir / output_name
        output_path.write_text(cleaned, encoding="utf-8")

        # Save cleaning metadata
        meta = {
            "source_file": str(filepath),
            "cleaned_file": str(output_path),
            "category": category,
            "doc_type": doc_type,
            "word_count": len(cleaned.split()),
            "cleaned_at": datetime.now(timezone.utc).isoformat(),
            "quality_valid": is_valid,
            "quality_issues": issues,
            "is_case_decision": is_decision,
        }
        meta_path = cleaned_dir / f"{output_name}.meta.json"
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        stats["files_cleaned"] += 1
        stats["total_words"] += len(cleaned.split())

    return stats


def _infer_doc_type(category: str, filename: str) -> str:
    """Infer document type from category and filename."""
    type_map = {
        "title_38_cfr": "cfr_part",
        "title_38_usc": "usc_chapter",
        "ucmj_10_usc": "usc_chapter",
        "bva_decisions": "bva_decision",
        "cavc_opinions": "cavc_opinion",
        "va_m21_1_manual": "m21_1_section",
        "vasrd_rating_schedule": "cfr_part",
    }

    if "reference" in filename.lower():
        return "reference"
    if "form" in filename.lower():
        return "form_info"

    return type_map.get(category, "default")


def run_cleaning_pipeline() -> dict:
    """Run the full cleaning pipeline across all source categories."""
    logger.info("=" * 60)
    logger.info("STARTING DATA CLEANING PIPELINE")
    logger.info("=" * 60)

    ensure_directories()
    deduplicator = Deduplicator()

    all_stats = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "categories": {},
        "totals": {
            "files_processed": 0,
            "files_cleaned": 0,
            "files_skipped": 0,
            "duplicates": 0,
            "quality_failures": 0,
            "total_words": 0,
        },
    }

    for category in SOURCE_CATEGORIES:
        logger.info(f"Processing category: {category}")
        cat_stats = process_category(category, deduplicator)
        all_stats["categories"][category] = cat_stats

        # Update totals
        for key in all_stats["totals"]:
            if key in cat_stats:
                all_stats["totals"][key] += cat_stats[key]

        logger.info(
            f"  {category}: {cat_stats['files_cleaned']} cleaned, "
            f"{cat_stats['files_skipped']} skipped, "
            f"{cat_stats['duplicates']} duplicates"
        )

    dedup_stats = deduplicator.get_stats()
    all_stats["deduplication"] = dedup_stats
    all_stats["completed_at"] = datetime.now(timezone.utc).isoformat()

    logger.info("=" * 60)
    logger.info(f"CLEANING COMPLETE")
    logger.info(f"  Files processed: {all_stats['totals']['files_processed']}")
    logger.info(f"  Files cleaned: {all_stats['totals']['files_cleaned']}")
    logger.info(f"  Duplicates removed: {all_stats['totals']['duplicates']}")
    logger.info(f"  Quality failures: {all_stats['totals']['quality_failures']}")
    logger.info(f"  Total words: {all_stats['totals']['total_words']:,}")
    logger.info("=" * 60)

    # Save cleaning report
    report_path = CLEANED_DIR / "cleaning_report.json"
    report_path.write_text(json.dumps(all_stats, indent=2), encoding="utf-8")

    return all_stats


if __name__ == "__main__":
    run_cleaning_pipeline()
