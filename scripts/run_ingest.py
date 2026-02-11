#!/usr/bin/env python3
"""
Valor Assist — Ingestion Runner

Run this script to ingest all documents from app/data/raw/ into ChromaDB.
Execute from the project root:

    python -m scripts.run_ingest
"""

import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingest import ingest_directory
from app.vector_store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-28s  %(levelname)-7s  %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=== Valor Assist — Document Ingestion ===")

    # 1. Ingest & chunk all raw documents
    chunks = ingest_directory()
    if not chunks:
        logger.error("No chunks produced. Add .txt or .md files to app/data/raw/")
        sys.exit(1)

    # 2. Embed & store in ChromaDB
    store = VectorStore()
    added = store.add_chunks(chunks)
    logger.info("Done — %d chunks stored in ChromaDB.", added)

    # 3. Quick sanity check: run a sample query
    test_query = "How do I appeal a PTSD denial?"
    logger.info("Running test query: '%s'", test_query)
    results = store.query(test_query, top_k=3)
    for i, r in enumerate(results, 1):
        meta = r["metadata"]
        logger.info(
            "  Result %d: %s [%s] (distance=%.4f)",
            i, meta.get("source_file"), meta.get("source_type"), r["distance"],
        )
        logger.info("    Preview: %s…", r["text"][:120])


if __name__ == "__main__":
    main()
