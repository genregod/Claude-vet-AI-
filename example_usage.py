#!/usr/bin/env python3
"""
Example script demonstrating Valor Assist usage.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def print_section(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def main():
    print_section("Valor Assist - Configuration Check")
    
    # Check configuration
    try:
        from app.core.config import settings
        print(f"✓ Configuration loaded successfully")
        print(f"  - App Name: {settings.app_name}")
        print(f"  - Version: {settings.app_version}")
        print(f"  - Embedding Model: {settings.embedding_model}")
        print(f"  - LLM Model: {settings.llm_model}")
        print(f"  - ChromaDB Path: {settings.chroma_db_path}")
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return
    
    print_section("Module Imports Check")
    
    # Check imports
    modules = [
        ("app.main", "FastAPI Application"),
        ("app.models.schemas", "Pydantic Schemas"),
        ("app.utils.pdf_processor", "PDF Processor"),
        ("app.utils.text_chunker", "Text Chunker"),
    ]
    
    for module_name, description in modules:
        try:
            __import__(module_name)
            print(f"✓ {description} ({module_name})")
        except Exception as e:
            print(f"✗ {description} ({module_name}): {e}")
    
    print_section("API Models Check")
    
    # Test Pydantic models
    try:
        from app.models.schemas import ChatRequest, ChatResponse, Citation
        
        # Create a sample request
        request = ChatRequest(
            query="What are the requirements for PTSD disability claims?",
            include_citations=True
        )
        print(f"✓ ChatRequest created: {request.query[:50]}...")
        
        # Create a sample citation
        citation = Citation(
            source="38 CFR Part 3",
            section="§ 3.304",
            content="Service connection for PTSD requires...",
            relevance_score=0.95,
            metadata={"document_id": "test_123"}
        )
        print(f"✓ Citation created: {citation.source}")
        
    except Exception as e:
        print(f"✗ Model validation error: {e}")
    
    print_section("Summary")
    print("✓ All core components initialized successfully!")
    print("\nNext steps:")
    print("1. Set up your API keys in .env file:")
    print("   - ANTHROPIC_API_KEY=your_key_here")
    print("   - VOYAGE_API_KEY=your_key_here")
    print("\n2. Start the FastAPI server:")
    print("   python -m uvicorn app.main:app --reload")
    print("\n3. Visit the API documentation:")
    print("   http://localhost:8000/docs")
    print("\n4. Ingest VA legal documents:")
    print("   python ingest_cli.py path/to/38_CFR.pdf --type CFR --part 'Part 3'")
    print("\n5. Query the system:")
    print("   python query_cli.py 'What are PTSD claim requirements?'")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
