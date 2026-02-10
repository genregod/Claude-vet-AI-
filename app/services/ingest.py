"""
Document ingestion module for loading VA legal documents into ChromaDB.
Supports 38 CFR, M21-1, and BVA decisions with metadata tagging.
"""
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import voyageai
import chromadb
from chromadb.config import Settings

from app.core.config import settings
from app.utils.pdf_processor import PDFCleaner, validate_pdf
from app.utils.text_chunker import LegalDocumentChunker, create_chunk_id

logger = logging.getLogger(__name__)


class DocumentIngestor:
    """Handles ingestion of VA legal documents into ChromaDB."""
    
    def __init__(self):
        """Initialize the document ingestor."""
        self.pdf_cleaner = PDFCleaner()
        self.chunker = LegalDocumentChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        
        # Initialize Voyage AI client for embeddings
        self.voyage_client = voyageai.Client(api_key=settings.voyage_api_key)
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=settings.chroma_db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"description": "VA legal documents for RAG"}
        )
        
        logger.info(f"Initialized DocumentIngestor with collection: {settings.chroma_collection_name}")
    
    def generate_document_id(self, file_path: Path, source_type: str) -> str:
        """
        Generate a unique document ID.
        
        Args:
            file_path: Path to the document
            source_type: Type of document (CFR, M21-1, BVA)
            
        Returns:
            Unique document ID
        """
        content = f"{file_path.name}_{source_type}_{file_path.stat().st_mtime}"
        doc_id = hashlib.md5(content.encode()).hexdigest()[:16]
        return f"{source_type}_{doc_id}"
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings using Voyage AI's voyage-law-2 model.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        logger.info(f"Creating embeddings for {len(texts)} chunks")
        
        # Voyage AI has a batch limit, process in batches if needed
        batch_size = 128
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            result = self.voyage_client.embed(
                batch,
                model=settings.embedding_model,
                input_type="document"
            )
            all_embeddings.extend(result.embeddings)
        
        logger.info(f"Created {len(all_embeddings)} embeddings")
        return all_embeddings
    
    def ingest_pdf(
        self,
        file_path: Path,
        source_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ingest a PDF document into ChromaDB.
        
        Args:
            file_path: Path to PDF file
            source_type: Type of document (CFR, M21-1, BVA)
            metadata: Additional metadata
            
        Returns:
            Ingestion results
        """
        if metadata is None:
            metadata = {}
        
        # Validate PDF
        if not validate_pdf(file_path, settings.pdf_max_size_mb):
            return {
                "success": False,
                "message": f"PDF validation failed for {file_path}",
                "document_id": None,
                "chunks_created": 0
            }
        
        try:
            # Generate document ID
            document_id = self.generate_document_id(file_path, source_type)
            
            # Extract and clean text
            logger.info(f"Processing PDF: {file_path}")
            result = self.pdf_cleaner.process_pdf(file_path)
            
            if not result["success"]:
                return {
                    "success": False,
                    "message": f"Failed to extract text from {file_path}",
                    "document_id": document_id,
                    "chunks_created": 0
                }
            
            # Prepare base metadata
            base_metadata = {
                "document_id": document_id,
                "source_type": source_type,
                "file_path": str(file_path),
                "ingestion_date": datetime.utcnow().isoformat(),
                **result["metadata"],
                **metadata
            }
            
            # Chunk the text
            chunks = self.chunker.chunk_text(result["text"], base_metadata)
            chunks = self.chunker.enhance_metadata(chunks)
            
            # Prepare data for ChromaDB
            chunk_ids = [create_chunk_id(document_id, i) for i in range(len(chunks))]
            chunk_texts = [chunk["text"] for chunk in chunks]
            chunk_metadatas = [chunk["metadata"] for chunk in chunks]
            
            # Create embeddings
            embeddings = self.create_embeddings(chunk_texts)
            
            # Add to ChromaDB
            logger.info(f"Adding {len(chunks)} chunks to ChromaDB")
            self.collection.add(
                ids=chunk_ids,
                embeddings=embeddings,
                documents=chunk_texts,
                metadatas=chunk_metadatas
            )
            
            logger.info(f"Successfully ingested {file_path} with {len(chunks)} chunks")
            
            return {
                "success": True,
                "message": f"Successfully ingested {file_path.name}",
                "document_id": document_id,
                "chunks_created": len(chunks)
            }
            
        except Exception as e:
            logger.error(f"Error ingesting {file_path}: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "document_id": None,
                "chunks_created": 0
            }
    
    def ingest_38_cfr(self, file_path: Path, part: Optional[str] = None) -> Dict[str, Any]:
        """
        Ingest 38 CFR (Code of Federal Regulations) document.
        
        Args:
            file_path: Path to CFR PDF
            part: CFR part number (e.g., "Part 3", "Part 4")
            
        Returns:
            Ingestion results
        """
        metadata = {
            "regulation_type": "38 CFR",
            "part": part or "Unknown"
        }
        return self.ingest_pdf(file_path, "CFR", metadata)
    
    def ingest_m21_1(self, file_path: Path, chapter: Optional[str] = None) -> Dict[str, Any]:
        """
        Ingest M21-1 Adjudication Procedures Manual.
        
        Args:
            file_path: Path to M21-1 PDF
            chapter: M21-1 chapter (e.g., "Chapter 3", "Part III")
            
        Returns:
            Ingestion results
        """
        metadata = {
            "manual": "M21-1",
            "chapter": chapter or "Unknown"
        }
        return self.ingest_pdf(file_path, "M21-1", metadata)
    
    def ingest_bva_decision(
        self,
        file_path: Path,
        decision_date: Optional[str] = None,
        citation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest BVA (Board of Veterans' Appeals) decision.
        
        Args:
            file_path: Path to BVA decision PDF
            decision_date: Date of the decision
            citation: BVA citation number
            
        Returns:
            Ingestion results
        """
        metadata = {
            "decision_type": "BVA",
            "decision_date": decision_date or "Unknown",
            "citation": citation or "Unknown"
        }
        return self.ingest_pdf(file_path, "BVA", metadata)
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the ChromaDB collection.
        
        Returns:
            Collection statistics
        """
        count = self.collection.count()
        return {
            "total_chunks": count,
            "collection_name": settings.chroma_collection_name,
            "embedding_model": settings.embedding_model
        }
    
    def delete_document(self, document_id: str) -> Dict[str, Any]:
        """
        Delete a document and all its chunks from ChromaDB.
        
        Args:
            document_id: ID of document to delete
            
        Returns:
            Deletion results
        """
        try:
            # Query for all chunks with this document_id
            results = self.collection.get(
                where={"document_id": document_id}
            )
            
            if not results['ids']:
                return {
                    "success": False,
                    "message": f"No chunks found for document {document_id}",
                    "chunks_deleted": 0
                }
            
            # Delete the chunks
            self.collection.delete(ids=results['ids'])
            
            logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
            
            return {
                "success": True,
                "message": f"Deleted document {document_id}",
                "chunks_deleted": len(results['ids'])
            }
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "chunks_deleted": 0
            }


# Singleton instance
_ingestor_instance = None


def get_ingestor() -> DocumentIngestor:
    """Get or create the document ingestor singleton."""
    global _ingestor_instance
    if _ingestor_instance is None:
        _ingestor_instance = DocumentIngestor()
    return _ingestor_instance
