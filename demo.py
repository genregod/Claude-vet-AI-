#!/usr/bin/env python3
"""
Demo script showcasing Valor Assist capabilities.
This simulates a typical user interaction.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


def print_header(text):
    """Print a formatted header."""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")


def print_citation(citation, index):
    """Print a formatted citation."""
    print(f"\n[{index}] {citation.source}")
    if citation.section:
        print(f"    Section: {citation.section}")
    print(f"    Relevance: {citation.relevance_score:.1%}")
    print(f"    Preview: {citation.content[:150]}...")


def demo_configuration():
    """Demo: Show configuration."""
    print_header("DEMO 1: Configuration Check")
    
    from app.core.config import settings
    
    print(f"Application: {settings.app_name} v{settings.app_version}")
    print(f"Embedding Model: {settings.embedding_model}")
    print(f"LLM Model: {settings.llm_model}")
    print(f"ChromaDB Path: {settings.chroma_db_path}")
    print(f"Top-K Results: {settings.top_k_results}")
    print("\n✓ Configuration loaded successfully")


def demo_models():
    """Demo: Show data models."""
    print_header("DEMO 2: Pydantic Data Models")
    
    from app.models.schemas import ChatRequest, ChatResponse, Citation
    from datetime import datetime, timezone
    
    # Create sample request
    request = ChatRequest(
        query="What are the requirements for PTSD disability claims?",
        conversation_history=[],
        include_citations=True
    )
    print("ChatRequest created:")
    print(f"  Query: {request.query}")
    print(f"  Include Citations: {request.include_citations}")
    
    # Create sample citation
    citation = Citation(
        source="38 CFR Part 3",
        section="§ 3.304(f)",
        content="Service connection for PTSD requires medical evidence...",
        relevance_score=0.95,
        metadata={"document_id": "CFR_abc123", "source_type": "CFR"}
    )
    print("\nCitation created:")
    print_citation(citation, 1)
    
    # Create sample response
    response = ChatResponse(
        response="Based on 38 CFR 3.304(f), PTSD claims require...",
        citations=[citation],
        timestamp=datetime.now(timezone.utc)
    )
    print(f"\nChatResponse created with {len(response.citations)} citation(s)")
    print("\n✓ All models validate successfully")


def demo_pdf_processing():
    """Demo: Show PDF processing capabilities."""
    print_header("DEMO 3: PDF Processing")
    
    from app.utils.pdf_processor import PDFCleaner
    
    cleaner = PDFCleaner()
    print("PDF Cleaner initialized with support for:")
    print("  - PyPDF (fast extraction)")
    print("  - pdfplumber (layout-aware)")
    print("  - PyMuPDF (complex layouts)")
    
    # Demo text cleaning
    sample_text = """
    This  is    a    sample    text
    with   multiple    spaces.
    
    
    
    And multiple newlines.
    
    Some-
    times words are hy-
    phenated.
    """
    
    cleaned = cleaner.clean_text(sample_text)
    print("\nOriginal text (with artifacts):")
    print(repr(sample_text[:100]))
    print("\nCleaned text:")
    print(repr(cleaned[:100]))
    print("\n✓ PDF processing ready")


def demo_text_chunking():
    """Demo: Show text chunking."""
    print_header("DEMO 4: Legal Document Chunking")
    
    from app.utils.text_chunker import LegalDocumentChunker
    
    chunker = LegalDocumentChunker(chunk_size=200, chunk_overlap=50)
    
    sample_text = """
§ 3.304 Direct service connection; wartime and peacetime.

Service connection may be established for disability resulting from personal injury suffered or disease contracted in line of duty, or for aggravation of a preexisting injury suffered or disease contracted in line of duty, in the active military, naval, or air service.

§ 3.305 Service connection; secondary conditions.

Service connection may be established for a disability which is proximately due to or the result of a service-connected disease or injury. Proximate cause is established by showing that the service-connected disability was a substantial factor in causing the secondary disability.
    """
    
    metadata = {
        "source_type": "CFR",
        "document_id": "CFR_test_123",
        "part": "Part 3"
    }
    
    chunks = chunker.chunk_text(sample_text, metadata)
    
    print(f"Created {len(chunks)} chunks from sample text")
    print(f"Chunk size target: {chunker.chunk_size} characters")
    print(f"Overlap: {chunker.chunk_overlap} characters")
    
    # Show first chunk
    if chunks:
        print("\nFirst chunk:")
        print(f"  Text: {chunks[0]['text'][:150]}...")
        print(f"  Metadata keys: {list(chunks[0]['metadata'].keys())}")
        print(f"  Chunk index: {chunks[0]['metadata']['chunk_index']}")
    
    print("\n✓ Chunking configured for legal documents")


def demo_api_structure():
    """Demo: Show API structure."""
    print_header("DEMO 5: API Endpoints")
    
    print("Available API endpoints:")
    print("\n1. Chat Endpoint")
    print("   POST /api/v1/chat")
    print("   - Submit questions about VA benefits")
    print("   - Receive AI-generated responses with citations")
    
    print("\n2. Ingest Endpoint")
    print("   POST /api/v1/ingest")
    print("   - Upload PDF documents (CFR, M21-1, BVA)")
    print("   - Automatic processing and embedding")
    
    print("\n3. Health Endpoint")
    print("   GET /api/v1/health")
    print("   - System health check")
    print("   - ChromaDB status")
    
    print("\n4. Stats Endpoint")
    print("   GET /api/v1/stats")
    print("   - Knowledge base statistics")
    print("   - Document counts")
    
    print("\n5. Delete Endpoint")
    print("   DELETE /api/v1/documents/{document_id}")
    print("   - Remove documents from knowledge base")
    
    print("\n✓ RESTful API ready")


def demo_summary():
    """Demo: Show summary."""
    print_header("DEMO COMPLETE - Summary")
    
    print("Valor Assist is ready to help Army veterans with VA disability claims!")
    print("\nKey Capabilities:")
    print("  ✓ RAG-powered question answering")
    print("  ✓ Legal citation extraction")
    print("  ✓ Multi-document ingestion (CFR, M21-1, BVA)")
    print("  ✓ Semantic search with Voyage-law-2")
    print("  ✓ Response generation with Claude-3-5-Sonnet")
    print("  ✓ RESTful API with FastAPI")
    print("  ✓ Docker deployment ready")
    
    print("\nTechnology Stack:")
    print("  • FastAPI - Modern web framework")
    print("  • Claude-3-5-Sonnet - Advanced reasoning")
    print("  • Voyage-law-2 - Legal embeddings")
    print("  • ChromaDB - Vector database")
    print("  • PyMuPDF, pdfplumber - PDF processing")
    
    print("\nNext Steps:")
    print("  1. Add your API keys to .env file")
    print("  2. Start the server: python -m uvicorn app.main:app --reload")
    print("  3. Visit http://localhost:8000/docs for interactive API docs")
    print("  4. Ingest VA documents: python ingest_cli.py <file> --type CFR")
    print("  5. Query the system: python query_cli.py '<question>'")
    
    print("\n" + "="*80)
    print("  Thank you for using Valor Assist!")
    print("  Supporting those who served. 🎖️")
    print("="*80 + "\n")


def main():
    """Run all demos."""
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + " "*25 + "VALOR ASSIST DEMO" + " "*37 + "█")
    print("█" + " "*20 + "VA Claims AI for Army Veterans" + " "*29 + "█")
    print("█" + " "*78 + "█")
    print("█"*80 + "\n")
    
    demos = [
        demo_configuration,
        demo_models,
        demo_pdf_processing,
        demo_text_chunking,
        demo_api_structure,
        demo_summary
    ]
    
    for i, demo in enumerate(demos, 1):
        try:
            demo()
            if i < len(demos):
                input("\nPress Enter to continue to next demo...")
        except Exception as e:
            print(f"\n✗ Demo failed: {e}")
            import traceback
            traceback.print_exc()
            continue


if __name__ == "__main__":
    main()
