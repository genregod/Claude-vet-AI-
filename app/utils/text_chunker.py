"""
Text chunking utilities for splitting documents into manageable pieces.
Implements semantic chunking for legal documents.
"""
import re
import logging
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class LegalDocumentChunker:
    """Chunks legal documents while preserving semantic meaning."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the chunker.
        
        Args:
            chunk_size: Target size for each chunk
            chunk_overlap: Overlap between chunks to preserve context
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Separators tuned for legal documents (CFR, M21-1, BVA decisions)
        self.separators = [
            "\n\n§",  # Section markers
            "\n\n",   # Paragraph breaks
            "\n",     # Line breaks
            ". ",     # Sentences
            "; ",     # Clauses
            ", ",     # Phrases
            " ",      # Words
            ""        # Characters
        ]
        
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=self.separators,
            length_function=len,
        )
    
    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Split text into chunks with metadata.
        
        Args:
            text: Text to chunk
            metadata: Base metadata to include with each chunk
            
        Returns:
            List of chunks with metadata
        """
        if metadata is None:
            metadata = {}
        
        # Split text into chunks
        chunks = self.splitter.split_text(text)
        
        # Add metadata to each chunk
        chunked_docs = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_index": i,
                "total_chunks": len(chunks),
                "chunk_size": len(chunk)
            })
            
            chunked_docs.append({
                "text": chunk,
                "metadata": chunk_metadata
            })
        
        logger.info(f"Created {len(chunks)} chunks from document")
        return chunked_docs
    
    def extract_section_number(self, text: str) -> str:
        """
        Extract section number from legal text (e.g., 38 CFR 3.102).
        
        Args:
            text: Text to search
            
        Returns:
            Section number or empty string
        """
        # Pattern for CFR sections
        cfr_pattern = r'(\d+\s+CFR\s+\d+\.\d+[a-z]?)'
        match = re.search(cfr_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Pattern for M21-1 sections
        m21_pattern = r'(M21-1[,\s]+(?:Part|Chapter|Section)\s+[IVX]+\.[a-z]+\.\d+)'
        match = re.search(m21_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Pattern for generic section markers
        section_pattern = r'§\s*(\d+\.\d+[a-z]?)'
        match = re.search(section_pattern, text)
        if match:
            return f"§ {match.group(1)}"
        
        return ""
    
    def enhance_metadata(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enhance chunk metadata with extracted information.
        
        Args:
            chunks: List of chunks to enhance
            
        Returns:
            Enhanced chunks
        """
        for chunk in chunks:
            text = chunk["text"]
            
            # Extract section number
            section = self.extract_section_number(text)
            if section:
                chunk["metadata"]["section"] = section
            
            # Detect document type from content
            if "38 CFR" in text or "Code of Federal Regulations" in text:
                chunk["metadata"]["inferred_type"] = "CFR"
            elif "M21-1" in text or "Adjudication Procedures Manual" in text:
                chunk["metadata"]["inferred_type"] = "M21-1"
            elif "Board of Veterans' Appeals" in text or "BVA" in text:
                chunk["metadata"]["inferred_type"] = "BVA"
        
        return chunks


def create_chunk_id(document_id: str, chunk_index: int) -> str:
    """
    Create a unique ID for a chunk.
    
    Args:
        document_id: ID of parent document
        chunk_index: Index of chunk within document
        
    Returns:
        Unique chunk ID
    """
    return f"{document_id}_chunk_{chunk_index}"
