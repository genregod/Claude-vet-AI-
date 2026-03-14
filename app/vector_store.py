"""
Valor Assist — Vector Store (OpenSearch Serverless + DynamoDB)

Replaces the ChromaDB implementation. Interface is identical so RAGChain
requires no changes.

query() flow:
  1. Embed query text via Voyage AI voyage-large-2
  2. k-NN search OpenSearch document-embeddings index
  3. Fetch chunk text + metadata from ValorAssist-DocumentMetadata DynamoDB
  4. Return list[dict] compatible with build_prompt() context_blocks format
"""

from __future__ import annotations

import logging

import boto3
import voyageai
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from boto3.dynamodb.conditions import Key

from app.config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self):
        self._voyage = voyageai.Client(api_key=settings.voyage_api_key)
        self._dynamo = boto3.resource("dynamodb", region_name=settings.aws_region)
        self._table = self._dynamo.Table("ValorAssist-DocumentMetadata")
        endpoint = settings.opensearch_endpoint.replace("https://", "")
        credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, settings.aws_region, "aoss")
        self._os = OpenSearch(
            hosts=[{"host": endpoint, "port": 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30,
        )
        self._index = settings.opensearch_index
        logger.info("VectorStore ready — index=%s", self._index)

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        source_type_filter: str | None = None,
    ) -> list[dict]:
        # 1. Embed
        embedding = self._voyage.embed([query_text], model="voyage-large-2").embeddings[0]

        # 2. Build k-NN query (with optional source_type post-filter)
        knn_query: dict = {"knn": {"embedding": {"vector": embedding, "k": top_k}}}
        if source_type_filter:
            os_query = {
                "size": top_k,
                "query": {
                    "bool": {
                        "must": [knn_query],
                        "filter": [{"term": {"sourceType": source_type_filter}}],
                    }
                },
            }
        else:
            os_query = {"size": top_k, "query": knn_query}

        resp = self._os.search(index=self._index, body=os_query)
        hits = resp["hits"]["hits"]
        if not hits:
            return []

        # 3. Fetch text + metadata from DynamoDB
        results: list[dict] = []
        for hit in hits:
            doc_id = hit["_source"].get("documentId")
            if not doc_id:
                continue
            item = self._table.get_item(Key={"documentId": doc_id}).get("Item")
            if not item:
                continue
            results.append({
                "text": item.get("text", ""),
                "metadata": {
                    "source_file": item.get("sourceFile", ""),
                    "source_type": item.get("sourceType", ""),
                    "chunk_index": item.get("chunkIndex", 0),
                    "total_chunks": 0,  # not stored; omit from display
                },
                "distance": 1.0 - hit.get("_score", 0.0),
            })

        return results
