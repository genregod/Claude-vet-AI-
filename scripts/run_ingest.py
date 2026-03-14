#!/usr/bin/env python3
"""
Valor Assist — Ingestion Runner (OpenSearch + DynamoDB)

Reads 38 CFR legal texts from app/data/raw/, chunks them, generates
Voyage AI voyage-large-2 embeddings, and stores:
  - Vectors + documentId  → OpenSearch Serverless (document-embeddings index)
  - Chunk text + metadata → ValorAssist-DocumentMetadata DynamoDB table

Run from project root:
    python -m scripts.run_ingest
"""

import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import boto3
import voyageai
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from opensearchpy.helpers import bulk

from app.ingest import ingest_directory

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(message)s")
logger = logging.getLogger(__name__)

VOYAGE_API_KEY      = os.environ["VOYAGE_API_KEY"]
OPENSEARCH_ENDPOINT = os.environ["OPENSEARCH_ENDPOINT"].replace("https://", "")
OPENSEARCH_INDEX    = os.environ.get("OPENSEARCH_INDEX", "document-embeddings")
AWS_REGION          = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
DYNAMO_TABLE        = "ValorAssist-DocumentMetadata"
EMBED_BATCH         = 32   # voyage-large-2 safe batch size
EMBED_RETRY_WAIT    = 30   # seconds to wait on rate limit


def os_client() -> OpenSearch:
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, AWS_REGION, "aoss")
    return OpenSearch(
        hosts=[{"host": OPENSEARCH_ENDPOINT, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )


def embed_with_retry(client: voyageai.Client, texts: list[str]) -> list[list[float]]:
    for attempt in range(3):
        try:
            return client.embed(texts, model="voyage-large-2").embeddings
        except Exception as e:
            if "rate" in str(e).lower() and attempt < 2:
                logger.warning("Rate limit — waiting %ds", EMBED_RETRY_WAIT)
                time.sleep(EMBED_RETRY_WAIT)
            else:
                raise
    raise RuntimeError("Embedding failed after retries")


def main():
    logger.info("=== Valor Assist — OpenSearch Ingestion ===")

    chunks = ingest_directory()
    if not chunks:
        logger.error("No chunks produced. Add .txt or .md files to app/data/raw/")
        sys.exit(1)
    logger.info("Chunked %d segments from raw documents", len(chunks))

    voyage  = voyageai.Client(api_key=VOYAGE_API_KEY)
    os_cli  = os_client()
    dynamo  = boto3.resource("dynamodb", region_name=AWS_REGION)
    table   = dynamo.Table(DYNAMO_TABLE)

    os_docs: list[dict] = []
    dynamo_items: list[dict] = []

    for i in range(0, len(chunks), EMBED_BATCH):
        batch = chunks[i : i + EMBED_BATCH]
        texts = [c.text for c in batch]
        logger.info("Embedding batch %d–%d …", i, i + len(batch))
        embeddings = embed_with_retry(voyage, texts)

        for chunk, embedding in zip(batch, embeddings):
            os_docs.append({
                "_index": OPENSEARCH_INDEX,
                "_source": {
                    "documentId": chunk.chunk_id,
                    "chunkIndex": chunk.metadata.get("chunk_index", 0),
                    "embedding":  embedding,
                },
            })
            dynamo_items.append({
                "documentId": chunk.chunk_id,
                "chunkIndex": chunk.metadata.get("chunk_index", 0),
                "text":       chunk.text,
                "sourceFile": chunk.metadata.get("source_file", ""),
                "sourceType": chunk.metadata.get("source_type", ""),
                "wordCount":  chunk.metadata.get("word_count", 0),
            })

    # Bulk write to OpenSearch
    logger.info("Writing %d vectors to OpenSearch …", len(os_docs))
    success, errors = bulk(os_cli, os_docs, raise_on_error=False)
    logger.info("OpenSearch: %d indexed, %d errors", success, len(errors))
    if errors:
        for e in errors[:5]:
            logger.warning("  OS error: %s", e)

    # Batch write to DynamoDB (25 items per batch_write_item call)
    logger.info("Writing %d items to DynamoDB …", len(dynamo_items))
    written = 0
    for i in range(0, len(dynamo_items), 25):
        batch_items = dynamo_items[i : i + 25]
        with table.batch_writer() as bw:
            for item in batch_items:
                bw.put_item(Item=item)
        written += len(batch_items)

    logger.info("DynamoDB: %d items written", written)
    logger.info("=== Ingestion complete ===")


if __name__ == "__main__":
    main()
