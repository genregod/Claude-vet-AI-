"""
Valor Assist — RAG Chain

Orchestrates the full Retrieval-Augmented Generation flow:

  1. Accept a user question (and optional source_type filter).
  2. Retrieve top-k relevant chunks from ChromaDB via semantic search.
  3. Assemble the chunks into the XML-tagged system prompt.
  4. Send the prompt to Claude 3.5 Sonnet via the Anthropic SDK.
  5. Return the model's cited, empathetic answer.

Supports two modes:
  • ask()      — multi-turn conversational chat (with session history)
  • evaluate() — one-shot case evaluation from the intake form

Uses the Anthropic Python SDK directly (not LangChain) to keep the
dependency surface small and the prompt control explicit.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import anthropic

from app.config import settings
from app.prompts import build_prompt, build_evaluation_prompt
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
    Holds a VectorStore handle and an Anthropic client.
    ask() supports multi-turn via the conversation_history parameter.
    """

    def __init__(self, vector_store: VectorStore | None = None):
        self._store = vector_store or VectorStore()
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        logger.info(
            "RAGChain ready — model=%s, top_k=%d",
            settings.claude_model,
            settings.retrieval_top_k,
        )

    def _extract_sources(self, retrieved: list[dict]) -> list[dict]:
        """Package retrieval results into a clean source list."""
        return [
            {
                "source_file": r["metadata"].get("source_file"),
                "source_type": r["metadata"].get("source_type"),
                "chunk_index": r["metadata"].get("chunk_index"),
                "relevance_distance": r["distance"],
            }
            for r in retrieved
        ]

    # ── Multi-turn chat ──────────────────────────────────────────────

    def ask(
        self,
        question: str,
        conversation_history: list[dict] | None = None,
        source_type_filter: str | None = None,
        top_k: int | None = None,
    ) -> RAGResponse:
        """
        End-to-end RAG with multi-turn support.

        Parameters
        ----------
        question : str
            The veteran's natural-language question.
        conversation_history : list[dict], optional
            Prior turns in [{"role": "user"|"assistant", "content": "..."}] format.
            Passed to Claude's messages API for conversational continuity.
        source_type_filter : str, optional
            Restrict retrieval to a specific source type.
        top_k : int, optional
            Override the default number of chunks to retrieve.
        """
        k = top_k or settings.retrieval_top_k

        # ── 1. Retrieve context for the current question ────────────
        logger.info("Retrieving top-%d chunks for: %s", k, question[:80])
        retrieved = self._store.query(
            query_text=question,
            top_k=k,
            source_type_filter=source_type_filter,
        )

        if not retrieved:
            logger.warning("No chunks retrieved — answering without context.")

        # ── 2. Build system prompt (context injected here) ──────────
        system_prompt = build_prompt(context_blocks=retrieved, question=question)

        # ── 3. Assemble messages array for multi-turn ───────────────
        # The system prompt carries the RAG context + instructions.
        # Conversation history provides continuity from prior turns.
        messages: list[dict] = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": question})

        # ── 4. Call Claude ──────────────────────────────────────────
        logger.info("Calling %s …", settings.claude_model)
        message = self._client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            temperature=settings.claude_temperature,
            system=system_prompt,
            messages=messages,
        )

        answer_text = message.content[0].text

        # ── 5. Package response ─────────────────────────────────────
        return RAGResponse(
            answer=answer_text,
            sources=self._extract_sources(retrieved),
            model=settings.claude_model,
            usage={
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens,
            },
        )

    # ── Case evaluation (one-shot) ───────────────────────────────────

    def evaluate(
        self,
        service_branch: str,
        current_rating: str,
        primary_concerns: str,
        additional_details: str = "",
        top_k: int | None = None,
    ) -> RAGResponse:
        """
        Run a structured case evaluation using the intake form data.
        Retrieves context relevant to the veteran's primary concerns,
        then uses the EVALUATION_PROMPT to generate an assessment.
        """
        k = top_k or settings.retrieval_top_k

        # Retrieve based on the veteran's stated concerns
        logger.info("Evaluating case — concerns: %s", primary_concerns[:80])
        retrieved = self._store.query(query_text=primary_concerns, top_k=k)

        system_prompt = build_evaluation_prompt(
            context_blocks=retrieved,
            service_branch=service_branch,
            current_rating=current_rating,
            primary_concerns=primary_concerns,
            additional_details=additional_details,
        )

        message = self._client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            temperature=settings.claude_temperature,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": "Please provide a preliminary case evaluation based on my profile.",
            }],
        )

        return RAGResponse(
            answer=message.content[0].text,
            sources=self._extract_sources(retrieved),
            model=settings.claude_model,
            usage={
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens,
            },
        )
