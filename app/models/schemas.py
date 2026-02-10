"""
Pydantic models for API requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone


class ChatMessage(BaseModel):
    """A single message in a chat conversation."""
    role: str = Field(..., description="Role of the message sender (user or assistant)")
    content: str = Field(..., description="Content of the message")


class ChatRequest(BaseModel):
    """Request model for the chat endpoint."""
    query: str = Field(..., description="User's question or query", min_length=1)
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=[],
        description="Previous messages in the conversation"
    )
    include_citations: bool = Field(
        default=True,
        description="Whether to include legal citations in the response"
    )


class Citation(BaseModel):
    """A legal citation with source metadata."""
    source: str = Field(..., description="Source document (e.g., 38 CFR, M21-1, BVA)")
    section: Optional[str] = Field(None, description="Specific section or regulation")
    content: str = Field(..., description="Relevant excerpt from the source")
    relevance_score: float = Field(..., description="Similarity score (0-1)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ChatResponse(BaseModel):
    """Response model for the chat endpoint."""
    response: str = Field(..., description="AI-generated response")
    citations: List[Citation] = Field(
        default=[],
        description="Legal citations supporting the response"
    )
    conversation_id: Optional[str] = Field(None, description="Unique conversation identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DocumentMetadata(BaseModel):
    """Metadata for ingested documents."""
    document_id: str = Field(..., description="Unique document identifier")
    source_type: str = Field(..., description="Type of document (CFR, M21-1, BVA)")
    title: str = Field(..., description="Document title")
    section: Optional[str] = Field(None, description="Section or part number")
    effective_date: Optional[str] = Field(None, description="Effective date of regulation")
    url: Optional[str] = Field(None, description="Source URL if available")
    page_count: Optional[int] = Field(None, description="Number of pages")
    file_path: str = Field(..., description="Path to source file")


class IngestRequest(BaseModel):
    """Request model for document ingestion."""
    file_path: str = Field(..., description="Path to the document to ingest")
    source_type: str = Field(..., description="Type of document (CFR, M21-1, BVA)")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class IngestResponse(BaseModel):
    """Response model for document ingestion."""
    success: bool = Field(..., description="Whether ingestion was successful")
    document_id: str = Field(..., description="Generated document ID")
    chunks_created: int = Field(..., description="Number of text chunks created")
    message: str = Field(..., description="Status message")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(default="healthy")
    version: str
    chroma_db_status: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
