"""
PDF processing utilities for cleaning and extracting text from VA legal documents.
Handles various PDF formats including scanned documents and complex layouts.
"""
import re
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import pypdf
import pdfplumber
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class PDFCleaner:
    """Cleans and processes PDF documents for ingestion."""
    
    def __init__(self):
        """Initialize PDF cleaner."""
        self.page_break_pattern = re.compile(r'\f')
        self.multiple_spaces = re.compile(r' {2,}')
        self.multiple_newlines = re.compile(r'\n{3,}')
        
    def extract_text_pypdf(self, pdf_path: Path) -> str:
        """
        Extract text using PyPDF (fast, simple extraction).
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n\n"
            return text
        except Exception as e:
            logger.error(f"PyPDF extraction failed for {pdf_path}: {e}")
            return ""
    
    def extract_text_pdfplumber(self, pdf_path: Path) -> str:
        """
        Extract text using pdfplumber (better layout preservation).
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
            return text
        except Exception as e:
            logger.error(f"pdfplumber extraction failed for {pdf_path}: {e}")
            return ""
    
    def extract_text_pymupdf(self, pdf_path: Path) -> str:
        """
        Extract text using PyMuPDF (best for complex layouts).
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        try:
            text = ""
            doc = fitz.open(pdf_path)
            for page in doc:
                text += page.get_text() + "\n\n"
            doc.close()
            return text
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed for {pdf_path}: {e}")
            return ""
    
    def extract_text(self, pdf_path: Path, method: str = "auto") -> str:
        """
        Extract text from PDF using the specified or best available method.
        
        Args:
            pdf_path: Path to PDF file
            method: Extraction method ('pypdf', 'pdfplumber', 'pymupdf', or 'auto')
            
        Returns:
            Extracted text
        """
        if method == "pypdf":
            return self.extract_text_pypdf(pdf_path)
        elif method == "pdfplumber":
            return self.extract_text_pdfplumber(pdf_path)
        elif method == "pymupdf":
            return self.extract_text_pymupdf(pdf_path)
        else:  # auto
            # Try methods in order of reliability for legal documents
            text = self.extract_text_pdfplumber(pdf_path)
            if not text or len(text) < 100:
                text = self.extract_text_pymupdf(pdf_path)
            if not text or len(text) < 100:
                text = self.extract_text_pypdf(pdf_path)
            return text
    
    def clean_text(self, text: str) -> str:
        """
        Clean extracted text by removing artifacts and normalizing formatting.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Remove page breaks
        text = self.page_break_pattern.sub('\n', text)
        
        # Remove excessive whitespace
        text = self.multiple_spaces.sub(' ', text)
        text = self.multiple_newlines.sub('\n\n', text)
        
        # Remove common PDF artifacts
        text = text.replace('\x00', '')
        text = text.replace('\uf0b7', '•')  # Fix bullet points
        
        # Normalize line breaks in middle of sentences
        # Keep paragraph breaks but join broken sentences
        lines = text.split('\n')
        cleaned_lines = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                cleaned_lines.append('')
                continue
                
            # If line ends with hyphen, join with next line
            if line.endswith('-') and i < len(lines) - 1:
                next_line = lines[i + 1].strip()
                if next_line and next_line[0].islower():
                    line = line[:-1] + next_line
                    lines[i + 1] = ''
            
            cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        text = self.multiple_newlines.sub('\n\n', text)
        
        return text.strip()
    
    def extract_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary of metadata
        """
        metadata = {
            "filename": pdf_path.name,
            "file_size": pdf_path.stat().st_size,
        }
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                metadata["page_count"] = len(pdf_reader.pages)
                
                if pdf_reader.metadata:
                    metadata.update({
                        "title": pdf_reader.metadata.get('/Title', ''),
                        "author": pdf_reader.metadata.get('/Author', ''),
                        "subject": pdf_reader.metadata.get('/Subject', ''),
                        "creator": pdf_reader.metadata.get('/Creator', ''),
                        "producer": pdf_reader.metadata.get('/Producer', ''),
                        "creation_date": pdf_reader.metadata.get('/CreationDate', ''),
                    })
        except Exception as e:
            logger.error(f"Metadata extraction failed for {pdf_path}: {e}")
        
        return metadata
    
    def process_pdf(self, pdf_path: Path, method: str = "auto") -> Dict[str, Any]:
        """
        Process a PDF file: extract text, clean it, and extract metadata.
        
        Args:
            pdf_path: Path to PDF file
            method: Extraction method to use
            
        Returns:
            Dictionary with cleaned text and metadata
        """
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Extract and clean text
        raw_text = self.extract_text(pdf_path, method)
        cleaned_text = self.clean_text(raw_text)
        
        # Extract metadata
        metadata = self.extract_metadata(pdf_path)
        
        return {
            "text": cleaned_text,
            "metadata": metadata,
            "success": len(cleaned_text) > 0
        }


def validate_pdf(pdf_path: Path, max_size_mb: int = 50) -> bool:
    """
    Validate PDF file before processing.
    
    Args:
        pdf_path: Path to PDF file
        max_size_mb: Maximum file size in MB
        
    Returns:
        True if valid, False otherwise
    """
    if not pdf_path.exists():
        logger.error(f"PDF file not found: {pdf_path}")
        return False
    
    if not pdf_path.suffix.lower() == '.pdf':
        logger.error(f"File is not a PDF: {pdf_path}")
        return False
    
    file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
    if file_size_mb > max_size_mb:
        logger.error(f"PDF file too large: {file_size_mb:.2f}MB (max: {max_size_mb}MB)")
        return False
    
    return True
