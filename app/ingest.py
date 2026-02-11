"""
Valor Assist — Document Ingestion & Chunking

Responsible for:
  1. Reading raw legal documents (.txt, .md, .pdf placeholder) from data/raw/
  2. Cleaning each document (PII redaction, header removal)
  3. Splitting into word-based chunks (~300-500 words) with overlap
  4. Tagging every chunk with metadata (source_type, filename, chunk_index)
  5. Returning structured records ready for embedding + vector storage

Source type detection uses filename conventions:
  - Files containing "38_cfr" or "cfr"      → tag "38_CFR"
  - Files containing "m21" or "m21-1"        → tag "M21-1_Manual"
  - Files containing "bva" or "decision"     → tag "BVA_Decision"
  - Files containing "usc" or "us_code"      → tag "US_Code"
  - Files containing "bcmr"                  → tag "BCMR"
  - Files containing "drb"                   → tag "DRB"
  - Files containing "cova" or "vet_app"     → tag "COVA"
  - Files containing "va_form"               → tag "VA_Form"
  - Everything else                          → tag "General"
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.config import settings, RAW_DOCS_DIR
from app.utils.text_cleaning import clean_document

logger = logging.getLogger(__name__)


# ── Data structures ──────────────────────────────────────────────────

@dataclass
class Chunk:
    """A single chunk ready for embedding."""
    text: str
    metadata: dict = field(default_factory=dict)
    chunk_id: str = ""

    def __post_init__(self):
        if not self.chunk_id:
            # Deterministic ID from content hash — avoids duplicates on re-ingest
            self.chunk_id = hashlib.sha256(self.text.encode()).hexdigest()[:16]


# ── Source-type tagging ──────────────────────────────────────────────

_SOURCE_TAG_RULES: list[tuple[list[str], str]] = [
    (["38_cfr", "cfr"],               "38_CFR"),
    (["m21-1", "m21_1", "m21"],       "M21-1_Manual"),
    (["bva", "decision"],             "BVA_Decision"),
    (["usc", "us_code"],              "US_Code"),
    (["bcmr"],                         "BCMR"),        # Board for Correction of Military Records
    (["drb"],                          "DRB"),         # Discharge Review Board
    (["cova", "vet_app", "cavc"],      "COVA"),        # Court of Appeals for Veterans Claims
    (["va_form"],                      "VA_Form"),     # VA form instructions / guidance
]


def detect_source_type(filename: str) -> str:
    """Infer the legal source type from the filename."""
    lower = filename.lower()
    for keywords, tag in _SOURCE_TAG_RULES:
        if any(kw in lower for kw in keywords):
            return tag
    return "General"


# ── Word-based chunking ─────────────────────────────────────────────

def chunk_text(
    text: str,
    chunk_size: int = settings.chunk_size_words,
    overlap: int = settings.chunk_overlap_words,
) -> list[str]:
    """
    Split *text* into chunks of approximately *chunk_size* words with
    *overlap* words carried over between consecutive chunks.

    We deliberately chunk by word count (not character count) because
    legal prose varies widely in sentence length, and word-based windows
    better preserve semantic coherence for downstream embedding.
    """
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        start += chunk_size - overlap  # slide window forward

    return chunks


# ── Full ingestion pipeline ──────────────────────────────────────────

def ingest_file(filepath: Path) -> list[Chunk]:
    """Read, clean, chunk, and tag a single document file."""
    logger.info("Ingesting %s", filepath.name)

    raw_text = filepath.read_text(encoding="utf-8", errors="replace")
    cleaned = clean_document(raw_text)

    if not cleaned.strip():
        logger.warning("File %s is empty after cleaning — skipping.", filepath.name)
        return []

    source_type = detect_source_type(filepath.name)
    raw_chunks = chunk_text(cleaned)

    chunks: list[Chunk] = []
    for idx, text in enumerate(raw_chunks):
        meta = {
            "source_file": filepath.name,
            "source_type": source_type,
            "chunk_index": idx,
            "total_chunks": len(raw_chunks),
            "word_count": len(text.split()),
        }
        chunks.append(Chunk(text=text, metadata=meta))

    logger.info(
        "  → %d chunks created (source_type=%s)", len(chunks), source_type
    )
    return chunks


def ingest_directory(directory: Path | None = None) -> list[Chunk]:
    """
    Ingest every supported file in *directory* (default: data/raw/).

    Returns a flat list of Chunk objects across all documents.
    """
    directory = directory or RAW_DOCS_DIR
    supported_extensions = {".txt", ".md"}

    all_chunks: list[Chunk] = []
    files = sorted(
        f for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in supported_extensions
    )

    if not files:
        logger.warning("No supported files found in %s", directory)
        return all_chunks

    for filepath in files:
        all_chunks.extend(ingest_file(filepath))

    logger.info("Total chunks ingested: %d from %d files", len(all_chunks), len(files))
    return all_chunks
