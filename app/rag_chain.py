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
from app.prompts import build_evaluation_prompt, build_prompt
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

    @staticmethod
    def _clean_response(text: str, max_chars: int = 500) -> str:
        """Strip markdown special characters and enforce character limit."""
        import re
        # Remove markdown: *, #, `, ~~, >, etc.
        text = re.sub(r'[*#`~>]', '', text)
        # Collapse multiple blank lines into one
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
        # Hard cap at max_chars, break at last sentence or word boundary
        if len(text) > max_chars:
            truncated = text[:max_chars]
            # Try to break at last period
            last_period = truncated.rfind('.')
            if last_period > max_chars * 0.5:
                text = truncated[:last_period + 1]
            else:
                # Break at last space
                last_space = truncated.rfind(' ')
                text = truncated[:last_space] + '...' if last_space > 0 else truncated
        return text

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

        # ── 4b. Clean response: strip markdown chars, cap at 500 chars
        answer_text = self._clean_response(answer_text)

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

    # ── Streaming chat ───────────────────────────────────────────────

    def ask_stream(
        self,
        question: str,
        conversation_history: list[dict] | None = None,
        source_type_filter: str | None = None,
        top_k: int | None = None,
    ):
        """Yield SSE-formatted text chunks from Claude for real-time streaming."""
        import json
        k = top_k or settings.retrieval_top_k
        retrieved = self._store.query(query_text=question, top_k=k, source_type_filter=source_type_filter)
        system_prompt = build_prompt(context_blocks=retrieved, question=question)
        messages: list[dict] = list(conversation_history or [])
        messages.append({"role": "user", "content": question})

        with self._client.messages.stream(
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            temperature=settings.claude_temperature,
            system=system_prompt,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'token': text})}\n\n"
        yield "data: [DONE]\n\n"

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

    # ── Battle Buddy (claude-opus-4-5 + extended thinking) ──────────────────

    def battle_buddy(
        self,
        question: str,
        conversation_history: list[dict] | None = None,
        top_k: int | None = None,
        profile_context: str = "",
    ) -> RAGResponse:
        """
        Battle Buddy chat using claude-opus-4-5 with extended thinking.
        Thinking blocks are stripped from the response; only text is returned.
        """
        from app.prompts import build_battle_buddy_prompt

        k = top_k or settings.retrieval_top_k
        retrieved = self._store.query(query_text=question, top_k=k)
        system_prompt = build_battle_buddy_prompt(context_blocks=retrieved)
        if profile_context:
            system_prompt = system_prompt + f"\n\n{profile_context}"

        messages: list[dict] = list(conversation_history or [])
        messages.append({"role": "user", "content": question})

        message = self._client.messages.create(
            model="claude-opus-4-5-20251101",
            max_tokens=16000,
            thinking={"type": "enabled", "budget_tokens": 10000},
            system=system_prompt,
            messages=messages,
        )

        # Extract only text blocks (skip thinking blocks)
        answer_text = " ".join(
            block.text for block in message.content if block.type == "text"
        ).strip()

        return RAGResponse(
            answer=answer_text,
            sources=self._extract_sources(retrieved),
            model="claude-opus-4-5-20251101",
            usage={
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens,
            },
        )

    # ── Profile Verification (claude-opus-4-5 + extended thinking) ──────────────

    def verify_profile(
        self,
        profile: dict,
        conversation_history: list[dict],
        confirmed_fields: list[str],
        skipped_fields: list[str],
        corrections: dict,
    ) -> dict:
        """
        Drive the human-in-the-loop profile verification conversation.

        Uses claude-opus-4-5 with extended thinking to reason through the profile,
        determine the next field to verify, and generate a structured response.

        Returns a dict matching the VERIFY_PROMPT output schema:
          message, section, field_path, progress, quick_replies,
          profile_update, confirmed_fields, skipped_fields, done
        """
        import json
        import re
        from app.prompts import build_verify_prompt

        system_prompt = build_verify_prompt(
            profile=profile,
            confirmed_fields=confirmed_fields,
            skipped_fields=skipped_fields,
            corrections=corrections,
        )

        messages: list[dict] = list(conversation_history[-6:])  # keep last 6 turns only
        # If no history yet, prime with a start signal
        if not messages:
            messages = [{"role": "user", "content": "Please begin the verification process."}]

        logger.info(
            "verify_profile — confirmed=%d skipped=%d history_turns=%d",
            len(confirmed_fields), len(skipped_fields), len(conversation_history),
        )

        message = self._client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        )

        # Extract text block (skip thinking blocks)
        raw = " ".join(
            block.text for block in message.content if block.type == "text"
        ).strip()

        # Strip markdown fences if model wraps in ```json
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
        raw = raw.strip()

        # Model sometimes prepends conversational text before the JSON object.
        # Find the first '{' and attempt to parse from there.
        json_start = raw.find("{")
        if json_start > 0:
            raw = raw[json_start:]

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("verify_profile JSON parse failed. Raw: %s", raw[:500])
            # Graceful fallback — ask the veteran to try again
            result = {
                "message": "I had trouble processing that. Could you repeat your last response?",
                "section": "unknown",
                "field_path": "",
                "progress": max(
                    round((len(confirmed_fields) + len(skipped_fields)) / max(1, len(confirmed_fields) + len(skipped_fields) + 5) * 100),
                    0,
                ),
                "quick_replies": ["Correct", "Not right", "More detail", "Skip for now"],
                "profile_update": None,
                "confirmed_fields": confirmed_fields,
                "skipped_fields": skipped_fields,
                "done": False,
            }

        result["_usage"] = {
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
        }
        return result
