"""
ChromaDB Ingest Pipeline

Loads cleaned documents into ChromaDB for the RAG knowledge base.
Chunks text, generates embeddings, and stores in the vector database.
"""

import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scripts.data_collection.config import (
    CLEANED_DIR,
    CHROMA_DIR,
    SOURCE_CATEGORIES,
    CHROMA_COLLECTION_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    ensure_directories,
)
from scripts.data_collection.logger import get_logger

logger = get_logger("pipeline.ingest")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEXT CHUNKING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """
    Split text into overlapping chunks for embedding.

    Uses sentence-aware splitting to avoid breaking mid-sentence.
    Each chunk includes metadata about its position.

    Args:
        text: Input text to chunk.
        chunk_size: Target chunk size in characters.
        overlap: Overlap between consecutive chunks.

    Returns:
        List of dicts with 'text', 'start_char', 'end_char', 'chunk_index'.
    """
    if not text or len(text) < 50:
        return []

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if not sentences:
        return []

    chunks = []
    current_chunk = []
    current_length = 0
    chunk_index = 0
    start_char = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        if current_length + sentence_len > chunk_size and current_chunk:
            # Emit current chunk
            chunk_text_str = " ".join(current_chunk)
            chunks.append({
                "text": chunk_text_str,
                "start_char": start_char,
                "end_char": start_char + len(chunk_text_str),
                "chunk_index": chunk_index,
            })
            chunk_index += 1

            # Calculate overlap — keep last few sentences
            overlap_sentences = []
            overlap_length = 0
            for s in reversed(current_chunk):
                if overlap_length + len(s) > overlap:
                    break
                overlap_sentences.insert(0, s)
                overlap_length += len(s)

            start_char = start_char + len(chunk_text_str) - overlap_length
            current_chunk = overlap_sentences
            current_length = overlap_length

        current_chunk.append(sentence)
        current_length += sentence_len

    # Emit final chunk
    if current_chunk:
        chunk_text_str = " ".join(current_chunk)
        chunks.append({
            "text": chunk_text_str,
            "start_char": start_char,
            "end_char": start_char + len(chunk_text_str),
            "chunk_index": chunk_index,
        })

    return chunks


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHROMADB MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ChromaDBManager:
    """Manages the ChromaDB collection for the knowledge base."""

    def __init__(self, persist_dir: Optional[Path] = None,
                 collection_name: str = CHROMA_COLLECTION_NAME):
        self.persist_dir = persist_dir or CHROMA_DIR
        self.collection_name = collection_name
        self._client = None
        self._collection = None

    @property
    def client(self):
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings
                self._client = chromadb.PersistentClient(
                    path=str(self.persist_dir),
                    settings=Settings(anonymized_telemetry=False),
                )
                logger.info(f"ChromaDB client initialized at {self.persist_dir}")
            except ImportError:
                logger.error("chromadb not installed. Run: pip install chromadb")
                raise
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Valor Assist veterans law knowledge base"},
            )
            logger.info(
                f"Collection '{self.collection_name}' ready "
                f"({self._collection.count()} existing documents)"
            )
        return self._collection

    def add_documents(self, texts: list[str], metadatas: list[dict],
                      ids: list[str]) -> int:
        """
        Add documents to the collection.

        Args:
            texts: List of text chunks.
            metadatas: List of metadata dicts for each chunk.
            ids: List of unique IDs for each chunk.

        Returns:
            Number of documents added.
        """
        if not texts:
            return 0

        # ChromaDB has a batch size limit
        batch_size = 100
        added = 0

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_metas = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]

            try:
                self.collection.upsert(
                    documents=batch_texts,
                    metadatas=batch_metas,
                    ids=batch_ids,
                )
                added += len(batch_texts)
            except Exception as e:
                logger.error(f"Failed to add batch {i // batch_size}: {e}")

        return added

    def get_count(self) -> int:
        """Get current document count."""
        return self.collection.count()

    def search(self, query: str, n_results: int = 5) -> dict:
        """Search the collection."""
        return self.collection.query(
            query_texts=[query],
            n_results=n_results,
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INGEST PIPELINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def ingest_category(db: ChromaDBManager, category: str) -> dict:
    """Ingest all cleaned documents from a single category."""
    cleaned_dir = CLEANED_DIR / category
    stats = {
        "category": category,
        "files_processed": 0,
        "chunks_created": 0,
        "chunks_ingested": 0,
    }

    if not cleaned_dir.exists():
        return stats

    all_texts = []
    all_metadatas = []
    all_ids = []

    for filepath in sorted(cleaned_dir.glob("*.txt")):
        if filepath.name.endswith(".meta.json"):
            continue

        text = filepath.read_text(encoding="utf-8", errors="replace")
        if len(text) < 50:
            continue

        stats["files_processed"] += 1

        # Load metadata if available
        meta_path = cleaned_dir / f"{filepath.name}.meta.json"
        file_meta = {}
        if meta_path.exists():
            try:
                file_meta = json.loads(meta_path.read_text())
            except json.JSONDecodeError:
                pass

        # Chunk the text
        chunks = chunk_text(text)
        stats["chunks_created"] += len(chunks)

        for chunk in chunks:
            chunk_id = hashlib.md5(
                f"{category}:{filepath.name}:{chunk['chunk_index']}".encode()
            ).hexdigest()

            chunk_meta = {
                "source_category": category,
                "source_file": filepath.name,
                "chunk_index": chunk["chunk_index"],
                "doc_type": file_meta.get("doc_type", "unknown"),
                "word_count": len(chunk["text"].split()),
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }

            all_texts.append(chunk["text"])
            all_metadatas.append(chunk_meta)
            all_ids.append(chunk_id)

    # Batch ingest
    if all_texts:
        ingested = db.add_documents(all_texts, all_metadatas, all_ids)
        stats["chunks_ingested"] = ingested

    return stats


def run_ingest_pipeline() -> dict:
    """Run the full ChromaDB ingestion pipeline."""
    logger.info("=" * 60)
    logger.info("STARTING CHROMADB INGEST PIPELINE")
    logger.info("=" * 60)

    ensure_directories()

    stats = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "categories": {},
        "totals": {
            "files_processed": 0,
            "chunks_created": 0,
            "chunks_ingested": 0,
        },
    }

    try:
        db = ChromaDBManager()
        initial_count = db.get_count()
        logger.info(f"Initial collection size: {initial_count} documents")

        for category in SOURCE_CATEGORIES:
            logger.info(f"Ingesting category: {category}")
            cat_stats = ingest_category(db, category)
            stats["categories"][category] = cat_stats

            for key in stats["totals"]:
                if key in cat_stats:
                    stats["totals"][key] += cat_stats[key]

            if cat_stats["chunks_ingested"] > 0:
                logger.info(
                    f"  {category}: {cat_stats['chunks_ingested']} chunks ingested "
                    f"from {cat_stats['files_processed']} files"
                )

        final_count = db.get_count()
        stats["final_collection_size"] = final_count
        stats["documents_added"] = final_count - initial_count

    except ImportError:
        logger.error("ChromaDB not installed. Install with: pip install chromadb")
        stats["error"] = "chromadb not installed"
    except Exception as e:
        logger.exception(f"Ingest pipeline failed: {e}")
        stats["error"] = str(e)

    stats["completed_at"] = datetime.now(timezone.utc).isoformat()

    logger.info("=" * 60)
    logger.info(f"INGEST COMPLETE")
    logger.info(f"  Files processed: {stats['totals']['files_processed']}")
    logger.info(f"  Chunks ingested: {stats['totals']['chunks_ingested']}")
    if "final_collection_size" in stats:
        logger.info(f"  Collection size: {stats['final_collection_size']}")
    logger.info("=" * 60)

    # Save ingest report
    report_path = CHROMA_DIR / "ingest_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    return stats


if __name__ == "__main__":
    run_ingest_pipeline()
