"""
RAG (Retrieval-Augmented Generation) module using Claude-3-5-Sonnet.
Implements semantic search with ChromaDB and generates responses with legal citations.
"""
import logging
from typing import List, Dict, Any, Optional
import voyageai
import chromadb
from chromadb.config import Settings
from anthropic import Anthropic

from app.core.config import settings
from app.models.schemas import Citation

logger = logging.getLogger(__name__)


class RAGPipeline:
    """RAG pipeline for VA legal question answering."""
    
    def __init__(self):
        """Initialize the RAG pipeline."""
        # Initialize Voyage AI client for query embeddings
        self.voyage_client = voyageai.Client(api_key=settings.voyage_api_key)
        
        # Initialize Anthropic Claude client
        self.anthropic_client = Anthropic(api_key=settings.anthropic_api_key)
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=settings.chroma_db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"description": "VA legal documents for RAG"}
        )
        
        logger.info("Initialized RAG pipeline")
    
    def create_query_embedding(self, query: str) -> List[float]:
        """
        Create embedding for a query using Voyage AI.
        
        Args:
            query: User query
            
        Returns:
            Query embedding vector
        """
        result = self.voyage_client.embed(
            [query],
            model=settings.embedding_model,
            input_type="query"
        )
        return result.embeddings[0]
    
    def retrieve_relevant_chunks(
        self,
        query: str,
        top_k: int = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant document chunks for a query.
        
        Args:
            query: User query
            top_k: Number of results to return
            filter_metadata: Metadata filters (e.g., {"source_type": "CFR"})
            
        Returns:
            List of relevant chunks with metadata and scores
        """
        if top_k is None:
            top_k = settings.top_k_results
        
        # Create query embedding
        query_embedding = self.create_query_embedding(query)
        
        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata if filter_metadata else None
        )
        
        # Format results
        chunks = []
        if results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                chunks.append({
                    "id": results['ids'][0][i],
                    "text": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if results.get('distances') else None
                })
        
        logger.info(f"Retrieved {len(chunks)} relevant chunks for query")
        return chunks
    
    def format_citations(self, chunks: List[Dict[str, Any]]) -> List[Citation]:
        """
        Format retrieved chunks as legal citations.
        
        Args:
            chunks: Retrieved chunks
            
        Returns:
            List of formatted citations
        """
        citations = []
        for i, chunk in enumerate(chunks, 1):
            metadata = chunk["metadata"]
            
            # Determine source
            source_type = metadata.get("source_type", "Unknown")
            section = metadata.get("section", "")
            
            if source_type == "CFR":
                source = f"38 CFR {metadata.get('part', '')}"
            elif source_type == "M21-1":
                source = f"M21-1 {metadata.get('chapter', '')}"
            elif source_type == "BVA":
                source = f"BVA Decision"
                if metadata.get("citation"):
                    source += f" ({metadata['citation']})"
            else:
                source = source_type
            
            # Calculate relevance score (inverse of distance, normalized)
            distance = chunk.get("distance", 1.0)
            relevance_score = max(0.0, 1.0 - distance)
            
            citation = Citation(
                source=source,
                section=section if section else None,
                content=chunk["text"][:500] + "..." if len(chunk["text"]) > 500 else chunk["text"],
                relevance_score=round(relevance_score, 3),
                metadata=metadata
            )
            citations.append(citation)
        
        return citations
    
    def build_context_from_chunks(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Build context string from retrieved chunks for the LLM.
        
        Args:
            chunks: Retrieved chunks
            
        Returns:
            Formatted context string
        """
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            metadata = chunk["metadata"]
            source = metadata.get("source_type", "Unknown")
            section = metadata.get("section", "")
            
            context_parts.append(
                f"<source id=\"{i}\" type=\"{source}\" section=\"{section}\">\n"
                f"{chunk['text']}\n"
                f"</source>"
            )
        
        return "\n\n".join(context_parts)
    
    def generate_response(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate a response using Claude with retrieved context.
        
        Args:
            query: User query
            context: Retrieved context from documents
            conversation_history: Previous conversation messages
            
        Returns:
            Generated response
        """
        if conversation_history is None:
            conversation_history = []
        
        # Build system prompt with XML-tagged instructions
        system_prompt = """You are a specialized AI assistant for VA (Veterans Affairs) disability claims, specifically designed to help Army veterans understand their benefits and navigate the claims process.

<role>
You are an expert legal assistant with deep knowledge of:
- 38 CFR (Code of Federal Regulations for Veterans Benefits)
- M21-1 Adjudication Procedures Manual
- BVA (Board of Veterans' Appeals) decisions
</role>

<instructions>
1. Provide accurate, helpful information based ONLY on the provided sources
2. Always cite specific regulations, sections, or decisions when making claims
3. Use XML tags to reference sources: <cite source="CFR" section="3.102">content</cite>
4. If information is not in the provided sources, clearly state this limitation
5. Be empathetic and supportive while remaining professional and accurate
6. Break down complex legal language into plain English for veterans
7. When discussing eligibility or requirements, list them clearly
8. Never provide medical or legal advice - only information from official sources
</instructions>

<tone>
Professional, empathetic, clear, and veteran-focused
</tone>"""

        # Build user message with context
        user_message = f"""<context>
{context}
</context>

<question>
{query}
</question>

Please answer the question based on the provided context. Use specific citations from the sources and format your response with clear references."""

        # Build messages array
        messages = []
        
        # Add conversation history
        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add current query
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Call Claude API
        logger.info(f"Generating response with Claude {settings.llm_model}")
        response = self.anthropic_client.messages.create(
            model=settings.llm_model,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
            system=system_prompt,
            messages=messages
        )
        
        # Extract response text
        response_text = response.content[0].text
        
        logger.info("Generated response successfully")
        return response_text
    
    def query(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        include_citations: bool = True,
        top_k: int = None
    ) -> Dict[str, Any]:
        """
        Execute full RAG pipeline: retrieve, augment, generate.
        
        Args:
            query: User query
            conversation_history: Previous conversation messages
            include_citations: Whether to return citations
            top_k: Number of documents to retrieve
            
        Returns:
            Dictionary with response and citations
        """
        logger.info(f"Processing query: {query[:100]}...")
        
        # Retrieve relevant chunks
        chunks = self.retrieve_relevant_chunks(query, top_k)
        
        if not chunks:
            logger.warning("No relevant documents found")
            return {
                "response": "I apologize, but I couldn't find relevant information in the VA legal documents to answer your question. Please try rephrasing your question or contact a VSO (Veterans Service Organization) for personalized assistance.",
                "citations": [],
                "chunks_retrieved": 0
            }
        
        # Build context
        context = self.build_context_from_chunks(chunks)
        
        # Generate response
        response = self.generate_response(query, context, conversation_history)
        
        # Format citations
        citations = self.format_citations(chunks) if include_citations else []
        
        return {
            "response": response,
            "citations": citations,
            "chunks_retrieved": len(chunks)
        }


# Singleton instance
_rag_instance = None


def get_rag_pipeline() -> RAGPipeline:
    """Get or create the RAG pipeline singleton."""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGPipeline()
    return _rag_instance
