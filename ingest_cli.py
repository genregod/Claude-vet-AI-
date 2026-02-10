#!/usr/bin/env python3
"""
Command-line script for ingesting VA legal documents.
"""
import sys
import argparse
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.ingest import get_ingestor
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Ingest VA legal documents into ChromaDB'
    )
    parser.add_argument(
        'file_path',
        type=str,
        help='Path to PDF file to ingest'
    )
    parser.add_argument(
        '--type',
        type=str,
        required=True,
        choices=['CFR', 'M21-1', 'BVA'],
        help='Type of document'
    )
    parser.add_argument(
        '--part',
        type=str,
        help='CFR part number (e.g., "Part 3")'
    )
    parser.add_argument(
        '--chapter',
        type=str,
        help='M21-1 chapter (e.g., "Chapter 3")'
    )
    parser.add_argument(
        '--decision-date',
        type=str,
        help='BVA decision date'
    )
    parser.add_argument(
        '--citation',
        type=str,
        help='BVA citation number'
    )
    
    args = parser.parse_args()
    
    # Validate file exists
    file_path = Path(args.file_path)
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        sys.exit(1)
    
    # Get ingestor
    logger.info("Initializing document ingestor...")
    ingestor = get_ingestor()
    
    # Ingest based on type
    logger.info(f"Ingesting {args.type} document: {file_path}")
    
    if args.type == "CFR":
        result = ingestor.ingest_38_cfr(file_path, args.part)
    elif args.type == "M21-1":
        result = ingestor.ingest_m21_1(file_path, args.chapter)
    elif args.type == "BVA":
        result = ingestor.ingest_bva_decision(
            file_path,
            args.decision_date,
            args.citation
        )
    else:
        logger.error(f"Invalid document type: {args.type}")
        sys.exit(1)
    
    # Print results
    if result["success"]:
        logger.info(f"✓ Success: {result['message']}")
        logger.info(f"  Document ID: {result['document_id']}")
        logger.info(f"  Chunks created: {result['chunks_created']}")
        
        # Print stats
        stats = ingestor.get_collection_stats()
        logger.info(f"  Total chunks in DB: {stats['total_chunks']}")
    else:
        logger.error(f"✗ Failed: {result['message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
