"""
Valor Assist — Vector Store (Embedding + ChromaDB)

Handles two embedding backends:
  • Voyage AI  voyage-law-2   — purpose-built for legal text (preferred)
  • HuggingFace sentence-transformers — free local fallback

ChromaDB is used as the local persistent vector database.  Each chunk is
stored with its embedding and full metadata dict, enabling filtered
retrieval by source_type at query time.
"""

from __future__ import annotations

import logging
from typing import Protocol

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings, CHROMA_DIR
from app.ingest import Chunk

logger = logging.getLogger(__name__)


# ── Embedding abstraction ────────────────────────────────────────────

class Embedder(Protocol):
    """Minimal interface every embedding backend must satisfy."""
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HuggingFaceEmbedder:
    """Wraps sentence-transformers for local, free-tier embedding."""

    def __init__(self, model_name: str = settings.hf_embedding_model):
        from sentence_transformers import SentenceTransformer
        logger.info("Loading HuggingFace model: %s", model_name)
        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()


class VoyageEmbedder:
    """
    Wraps the Voyage AI API for legal-optimized embeddings.
    Requires VOYAGE_API_KEY in the environment.
    """

    def __init__(
        self,
        model: str = settings.voyage_model,
        api_key: str = settings.voyage_api_key,
    ):
        import voyageai  # type: ignore[import-untyped]
        self._client = voyageai.Client(api_key=api_key)
        self._model = model
        logger.info("Using Voyage AI model: %s", model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = self._client.embed(texts, model=self._model)
                return result.embeddings
            except Exception as e:
                if "RateLimitError" in type(e).__name__ or "rate" in str(e).lower():
                    wait = 20 * (attempt + 1)  # 20s, 40s, 60s
                    logger.warning("Voyage AI rate limit hit, waiting %ds…", wait)
                    time.sleep(wait)
                else:
                    raise
        # Final attempt — let it raise if it fails
        result = self._client.embed(texts, model=self._model)
        return result.embeddings


def get_embedder() -> Embedder:
    """Factory — returns the embedder configured in settings."""
    if settings.embedding_provider == "voyageai" and settings.voyage_api_key:
        return VoyageEmbedder()
    return HuggingFaceEmbedder()


# ── ChromaDB wrapper ─────────────────────────────────────────────────

class VectorStore:
    """Thin wrapper around a ChromaDB persistent collection."""

    def __init__(self, embedder: Embedder | None = None):
        self._embedder = embedder or get_embedder()
        self._client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "ChromaDB collection '%s' ready (%d existing documents)",
            settings.chroma_collection_name,
            self._collection.count(),
        )

    # ── Write ────────────────────────────────────────────────────────

    def add_chunks(self, chunks: list[Chunk], batch_size: int = 64) -> int:
        """
        Embed and upsert a list of Chunk objects into ChromaDB.
        Returns the number of chunks stored.
        """
        if not chunks:
            return 0

        total_added = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c.text for c in batch]
            ids = [c.chunk_id for c in batch]
            metas = [c.metadata for c in batch]

            embeddings = self._embedder.embed(texts)

            self._collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metas,
            )
            total_added += len(batch)
            logger.info("  upserted batch %d–%d", i, i + len(batch))

        logger.info("Total documents in collection: %d", self._collection.count())
        return total_added

    # ── Read ─────────────────────────────────────────────────────────

    def query(
        self,
        query_text: str,
        top_k: int = settings.retrieval_top_k,
        source_type_filter: str | None = None,
    ) -> list[dict]:
        """
        Semantic search: embed *query_text*, find the closest *top_k*
        chunks, optionally filtered by source_type metadata.

        Returns a list of dicts:
            [{"text": ..., "metadata": ..., "distance": ...}, ...]
        """
        query_embedding = self._embedder.embed([query_text])[0]

        where_filter = None
        if source_type_filter:
            where_filter = {"source_type": source_type_filter}

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        # Unpack ChromaDB's nested list structure
        docs = results["documents"][0] if results["documents"] else []
        metas = results["metadatas"][0] if results["metadatas"] else []
        dists = results["distances"][0] if results["distances"] else []

        return [
            {"text": doc, "metadata": meta, "distance": dist}
            for doc, meta, dist in zip(docs, metas, dists)
        ]

    @property
    def count(self) -> int:
        return self._collection.count()
