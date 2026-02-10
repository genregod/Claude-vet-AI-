"""
API endpoints for Valor Assist.
"""
import logging
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from datetime import datetime, timezone

from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    IngestRequest,
    IngestResponse,
    HealthResponse,
    Citation
)
from app.services.rag import get_rag_pipeline
from app.services.ingest import get_ingestor
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint for VA claims questions.
    Uses RAG pipeline with Claude-3-5-Sonnet for responses.
    
    Args:
        request: Chat request with query and optional conversation history
        
    Returns:
        ChatResponse with AI-generated answer and legal citations
    """
    try:
        logger.info(f"Received chat request: {request.query[:100]}...")
        
        # Get RAG pipeline
        rag = get_rag_pipeline()
        
        # Convert conversation history to dict format
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ] if request.conversation_history else []
        
        # Execute RAG query
        result = rag.query(
            query=request.query,
            conversation_history=conversation_history,
            include_citations=request.include_citations
        )
        
        # Build response
        response = ChatResponse(
            response=result["response"],
            citations=result.get("citations", []),
            conversation_id=None,  # Could implement conversation tracking
            timestamp=datetime.now(timezone.utc)
        )
        
        logger.info("Chat response generated successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    source_type: str = Form(...),
    part: Optional[str] = Form(None),
    chapter: Optional[str] = Form(None),
    decision_date: Optional[str] = Form(None),
    citation: Optional[str] = Form(None)
):
    """
    Ingest a PDF document into the knowledge base.
    
    Args:
        file: PDF file to ingest
        source_type: Type of document (CFR, M21-1, BVA)
        part: CFR part number (for CFR documents)
        chapter: Chapter (for M21-1 documents)
        decision_date: Decision date (for BVA decisions)
        citation: Citation number (for BVA decisions)
        
    Returns:
        IngestResponse with ingestion results
    """
    try:
        # Validate source type
        valid_types = ["CFR", "M21-1", "BVA"]
        if source_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source_type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Sanitize filename to prevent path traversal
        sanitized_filename = Path(file.filename).name
        temp_path = Path(f"/tmp/{sanitized_filename}")
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"Ingesting document: {sanitized_filename} (type: {source_type})")
        
        # Get ingestor
        ingestor = get_ingestor()
        
        # Ingest based on type
        if source_type == "CFR":
            result = ingestor.ingest_38_cfr(temp_path, part)
        elif source_type == "M21-1":
            result = ingestor.ingest_m21_1(temp_path, chapter)
        elif source_type == "BVA":
            result = ingestor.ingest_bva_decision(temp_path, decision_date, citation)
        else:
            result = ingestor.ingest_pdf(temp_path, source_type)
        
        # Clean up temp file
        temp_path.unlink(missing_ok=True)
        
        # Build response
        response = IngestResponse(
            success=result["success"],
            document_id=result["document_id"] or "unknown",
            chunks_created=result["chunks_created"],
            message=result["message"]
        )
        
        if not result["success"]:
            logger.warning(f"Ingestion failed: {result['message']}")
        else:
            logger.info(f"Successfully ingested {file.filename}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error ingesting document: {str(e)}")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        HealthResponse with system status
    """
    try:
        # Check ChromaDB connection
        ingestor = get_ingestor()
        stats = ingestor.get_collection_stats()
        chroma_status = f"Connected ({stats['total_chunks']} chunks)"
        
        return HealthResponse(
            status="healthy",
            version=settings.app_version,
            chroma_db_status=chroma_status,
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            version=settings.app_version,
            chroma_db_status=f"Error: {str(e)}",
            timestamp=datetime.now(timezone.utc)
        )


@router.get("/stats")
async def get_stats():
    """
    Get statistics about the knowledge base.
    
    Returns:
        Statistics dictionary
    """
    try:
        ingestor = get_ingestor()
        stats = ingestor.get_collection_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document from the knowledge base.
    
    Args:
        document_id: ID of document to delete
        
    Returns:
        Deletion results
    """
    try:
        ingestor = get_ingestor()
        result = ingestor.delete_document(document_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")
