#!/usr/bin/env python3
"""
Command-line script for querying the RAG pipeline.
"""
import sys
import argparse
from pathlib import Path
import logging
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.rag import get_rag_pipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Query the VA legal RAG pipeline'
    )
    parser.add_argument(
        'query',
        type=str,
        help='Question to ask'
    )
    parser.add_argument(
        '--no-citations',
        action='store_true',
        help='Disable citation output'
    )
    parser.add_argument(
        '--top-k',
        type=int,
        default=5,
        help='Number of documents to retrieve (default: 5)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )
    
    args = parser.parse_args()
    
    # Get RAG pipeline
    logger.info("Initializing RAG pipeline...")
    rag = get_rag_pipeline()
    
    # Execute query
    logger.info(f"Processing query: {args.query}")
    result = rag.query(
        query=args.query,
        include_citations=not args.no_citations,
        top_k=args.top_k
    )
    
    # Output results
    if args.json:
        # JSON output
        output = {
            "query": args.query,
            "response": result["response"],
            "citations": [
                {
                    "source": c.source,
                    "section": c.section,
                    "relevance_score": c.relevance_score,
                    "content": c.content[:200] + "..."
                }
                for c in result.get("citations", [])
            ],
            "chunks_retrieved": result.get("chunks_retrieved", 0)
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        print("\n" + "="*80)
        print("QUESTION:")
        print(args.query)
        print("\n" + "="*80)
        print("ANSWER:")
        print(result["response"])
        
        if result.get("citations") and not args.no_citations:
            print("\n" + "="*80)
            print("CITATIONS:")
            for i, citation in enumerate(result["citations"], 1):
                print(f"\n[{i}] {citation.source}")
                if citation.section:
                    print(f"    Section: {citation.section}")
                print(f"    Relevance: {citation.relevance_score:.2%}")
                print(f"    Excerpt: {citation.content[:200]}...")
        
        print("\n" + "="*80)
        print(f"Retrieved {result.get('chunks_retrieved', 0)} relevant chunks")
        print("="*80 + "\n")


if __name__ == "__main__":
    main()
