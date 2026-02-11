"""
Valor Assist — FastAPI Server

Exposes the RAG pipeline through HTTP endpoints:

  POST /chat          — primary Q&A endpoint for veterans
  GET  /health        — liveness check
  GET  /stats         — vector store statistics
  POST /ingest        — trigger document re-ingestion (admin)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.ingest import ingest_directory
from app.rag_chain import RAGChain
from app.vector_store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-28s  %(levelname)-7s  %(message)s",
)
logger = logging.getLogger(__name__)


# ── Application lifespan (startup / shutdown) ────────────────────────

rag_chain: RAGChain | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the vector store and RAG chain once at startup."""
    global rag_chain
    logger.info("Starting Valor Assist backend …")
    store = VectorStore()
    rag_chain = RAGChain(vector_store=store)
    logger.info("RAG chain initialized — ready to serve.")
    yield
    logger.info("Shutting down Valor Assist backend.")


app = FastAPI(
    title="Valor Assist",
    description=(
        "AI-powered assistant helping U.S. Army veterans navigate "
        "VA disability claims, appeals, and 38 CFR regulations."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


# ── Request / Response schemas ───────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="The veteran's question about VA claims or regulations.",
        json_schema_extra={
            "examples": ["How do I appeal a PTSD denial?"],
        },
    )
    source_type_filter: str | None = Field(
        default=None,
        description=(
            "Optional: restrict retrieval to a specific source type. "
            "Values: 38_CFR, M21-1_Manual, BVA_Decision, US_Code, General."
        ),
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=10,
        description="Override default number of context chunks to retrieve.",
    )


class SourceInfo(BaseModel):
    source_file: str | None
    source_type: str | None
    chunk_index: int | None
    relevance_distance: float | None


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceInfo]
    model: str
    usage: dict


class IngestResponse(BaseModel):
    status: str
    chunks_ingested: int
    total_documents: int


# ── Endpoints ────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Primary Q&A endpoint.

    Accepts a veteran's question, retrieves relevant legal context from
    the vector store, sends the assembled prompt to Claude 3.5 Sonnet,
    and returns a cited, empathetic answer.
    """
    if rag_chain is None:
        raise HTTPException(status_code=503, detail="RAG chain not initialized.")

    try:
        result = rag_chain.ask(
            question=request.question,
            source_type_filter=request.source_type_filter,
            top_k=request.top_k,
        )
    except Exception as exc:
        logger.exception("Error processing chat request")
        raise HTTPException(status_code=500, detail=str(exc))

    return ChatResponse(
        answer=result.answer,
        sources=[SourceInfo(**s) for s in result.sources],
        model=result.model,
        usage=result.usage,
    )


@app.get("/health")
async def health():
    """Liveness probe."""
    return {"status": "ok", "model": settings.claude_model}


@app.get("/stats")
async def stats():
    """Return vector store statistics."""
    if rag_chain is None:
        raise HTTPException(status_code=503, detail="RAG chain not initialized.")
    return {
        "collection": settings.chroma_collection_name,
        "document_count": rag_chain._store.count,
        "embedding_provider": settings.embedding_provider,
    }


@app.post("/ingest", response_model=IngestResponse)
async def ingest():
    """
    Admin endpoint: re-ingest all documents from data/raw/ into the
    vector store. Useful after adding new legal texts.
    """
    if rag_chain is None:
        raise HTTPException(status_code=503, detail="RAG chain not initialized.")

    chunks = ingest_directory()
    count = rag_chain._store.add_chunks(chunks)

    return IngestResponse(
        status="success",
        chunks_ingested=count,
        total_documents=rag_chain._store.count,
    )


# ── Entrypoint ───────────────────────────────────────────────────────

def main():
    """Run with: python -m app.server"""
    import uvicorn
    uvicorn.run(
        "app.server:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
