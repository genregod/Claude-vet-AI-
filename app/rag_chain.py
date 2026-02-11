"""
Valor Assist — RAG Chain

Orchestrates the full Retrieval-Augmented Generation flow:

  1. Accept a user question (and optional source_type filter).
  2. Retrieve top-k relevant chunks from ChromaDB via semantic search.
  3. Assemble the chunks into the XML-tagged system prompt.
  4. Send the prompt to Claude 3.5 Sonnet via the Anthropic SDK.
  5. Return the model's cited, empathetic answer.

Uses the Anthropic Python SDK directly (not LangChain) to keep the
dependency surface small and the prompt control explicit.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import anthropic

from app.config import settings
from app.prompts import build_prompt
from app.vector_store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """Structured response returned to the API layer."""
    answer: str
    sources: list[dict]
    model: str
    usage: dict


class RAGChain:
    """
    Stateless-ish chain: holds a VectorStore handle and an Anthropic
    client, but each call to `ask()` is independent.
    """

    def __init__(self, vector_store: VectorStore | None = None):
        self._store = vector_store or VectorStore()
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        logger.info(
            "RAGChain ready — model=%s, top_k=%d",
            settings.claude_model,
            settings.retrieval_top_k,
        )

    def ask(
        self,
        question: str,
        source_type_filter: str | None = None,
        top_k: int | None = None,
    ) -> RAGResponse:
        """
        End-to-end RAG: retrieve → prompt → call Claude → return.

        Parameters
        ----------
        question : str
            The veteran's natural-language question.
        source_type_filter : str, optional
            Restrict retrieval to a specific source type
            (e.g. "38_CFR", "BVA_Decision").
        top_k : int, optional
            Override the default number of chunks to retrieve.
        """
        k = top_k or settings.retrieval_top_k

        # ── 1. Retrieve ─────────────────────────────────────────────
        logger.info("Retrieving top-%d chunks for: %s", k, question[:80])
        retrieved = self._store.query(
            query_text=question,
            top_k=k,
            source_type_filter=source_type_filter,
        )

        if not retrieved:
            logger.warning("No chunks retrieved — answering without context.")

        # ── 2. Build prompt ──────────────────────────────────────────
        system_prompt = build_prompt(context_blocks=retrieved, question=question)

        # ── 3. Call Claude ───────────────────────────────────────────
        logger.info("Calling %s …", settings.claude_model)
        message = self._client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            temperature=settings.claude_temperature,
            messages=[{"role": "user", "content": system_prompt}],
        )

        answer_text = message.content[0].text

        # ── 4. Package response ─────────────────────────────────────
        sources = [
            {
                "source_file": r["metadata"].get("source_file"),
                "source_type": r["metadata"].get("source_type"),
                "chunk_index": r["metadata"].get("chunk_index"),
                "relevance_distance": r["distance"],
            }
            for r in retrieved
        ]

        return RAGResponse(
            answer=answer_text,
            sources=sources,
            model=settings.claude_model,
            usage={
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens,
            },
        )
