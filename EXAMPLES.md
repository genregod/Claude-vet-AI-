# Valor Assist - Usage Examples

This document provides detailed examples of using Valor Assist for VA disability claims assistance.

## Table of Contents

1. [Basic Chat Queries](#basic-chat-queries)
2. [Document Ingestion](#document-ingestion)
3. [Advanced Queries](#advanced-queries)
4. [API Integration](#api-integration)
5. [Python SDK Examples](#python-sdk-examples)

## Basic Chat Queries

### Example 1: General PTSD Information

**CLI:**
```bash
python query_cli.py "What conditions must be met for a PTSD claim?"
```

**API:**
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What conditions must be met for a PTSD claim?",
    "include_citations": true
  }'
```

**Expected Response:**
```json
{
  "response": "Based on 38 CFR 3.304(f), service connection for PTSD requires...",
  "citations": [
    {
      "source": "38 CFR Part 3",
      "section": "§ 3.304",
      "content": "Service connection for PTSD requires...",
      "relevance_score": 0.92
    }
  ],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Example 2: Service Connection Requirements

**Query:**
```bash
python query_cli.py "What is needed to establish service connection for hearing loss?"
```

**Key Points:**
- System retrieves relevant CFR sections
- Provides specific regulatory citations
- Includes evidence requirements

## Document Ingestion

### Example 1: Ingest 38 CFR Part 3

```bash
python ingest_cli.py ./data/raw/38_CFR_Part_3.pdf \
  --type CFR \
  --part "Part 3"
```

**What Happens:**
1. PDF is extracted and cleaned
2. Text is chunked with semantic awareness
3. Each chunk gets a Voyage-law-2 embedding
4. Chunks stored in ChromaDB with metadata

### Example 2: Ingest M21-1 Manual

```bash
python ingest_cli.py ./data/raw/M21-1_Ch4_PTSD.pdf \
  --type M21-1 \
  --chapter "Chapter 4"
```

### Example 3: Ingest BVA Decision

```bash
python ingest_cli.py ./data/raw/BVA_20-1234.pdf \
  --type BVA \
  --decision-date "2020-05-15" \
  --citation "20-1234"
```

### Example 4: Batch Ingestion

```bash
# Shell script for batch ingestion
for file in data/raw/CFR/*.pdf; do
  python ingest_cli.py "$file" --type CFR --part "$(basename "$file" .pdf)"
  sleep 2  # Rate limiting
done
```

## Advanced Queries

### Example 1: Multiple Document Types

```bash
python query_cli.py \
  "How do CFR and M21-1 differ on secondary service connection?" \
  --top-k 8
```

This retrieves context from both CFR and M21-1, allowing Claude to compare.

### Example 2: Specific Regulation Lookup

```bash
python query_cli.py "Explain 38 CFR 3.310" --top-k 3
```

### Example 3: Case Law Integration

```bash
python query_cli.py \
  "What BVA decisions relate to TDIU and unemployability?" \
  --top-k 10
```

## API Integration

### Example 1: Simple Python Client

```python
import requests

API_URL = "http://localhost:8000/api/v1"

def chat(query, include_citations=True):
    response = requests.post(
        f"{API_URL}/chat",
        json={
            "query": query,
            "include_citations": include_citations
        }
    )
    return response.json()

# Use it
result = chat("What is the VA rating schedule for PTSD?")
print(result["response"])
for citation in result["citations"]:
    print(f"- {citation['source']}: {citation['section']}")
```

### Example 2: Conversation History

```python
def chat_with_history(query, history=[]):
    response = requests.post(
        f"{API_URL}/chat",
        json={
            "query": query,
            "conversation_history": history,
            "include_citations": True
        }
    )
    return response.json()

# Multi-turn conversation
history = []

# First question
result1 = chat_with_history("What is service connection?")
history.append({"role": "user", "content": "What is service connection?"})
history.append({"role": "assistant", "content": result1["response"]})

# Follow-up
result2 = chat_with_history("What about secondary conditions?", history)
print(result2["response"])
```

### Example 3: Document Upload with JavaScript

```javascript
async function uploadDocument(file, sourceType, metadata = {}) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('source_type', sourceType);
  
  if (metadata.part) formData.append('part', metadata.part);
  if (metadata.chapter) formData.append('chapter', metadata.chapter);
  
  const response = await fetch('http://localhost:8000/api/v1/ingest', {
    method: 'POST',
    body: formData
  });
  
  return await response.json();
}

// Usage
const fileInput = document.querySelector('#pdfFile');
const result = await uploadDocument(
  fileInput.files[0],
  'CFR',
  { part: 'Part 3' }
);
console.log(`Ingested: ${result.chunks_created} chunks`);
```

## Python SDK Examples

### Example 1: Direct RAG Pipeline Usage

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.rag import get_rag_pipeline

# Initialize
rag = get_rag_pipeline()

# Query
result = rag.query(
    query="What is the effective date for PTSD claims?",
    include_citations=True,
    top_k=5
)

print(f"Response: {result['response']}\n")
print(f"Citations: {len(result['citations'])}")
for citation in result['citations']:
    print(f"  - {citation.source} ({citation.relevance_score:.2%})")
```

### Example 2: Custom Ingestion

```python
from pathlib import Path
from app.services.ingest import get_ingestor

# Initialize
ingestor = get_ingestor()

# Ingest with custom metadata
result = ingestor.ingest_pdf(
    file_path=Path("data/raw/special_doc.pdf"),
    source_type="CFR",
    metadata={
        "part": "Part 4",
        "effective_date": "2024-01-01",
        "custom_tag": "rating_schedule"
    }
)

print(f"Success: {result['success']}")
print(f"Document ID: {result['document_id']}")
print(f"Chunks: {result['chunks_created']}")
```

### Example 3: Retrieve Statistics

```python
from app.services.ingest import get_ingestor

ingestor = get_ingestor()
stats = ingestor.get_collection_stats()

print(f"Total chunks in database: {stats['total_chunks']}")
print(f"Collection: {stats['collection_name']}")
print(f"Embedding model: {stats['embedding_model']}")
```

## Use Case Scenarios

### Scenario 1: VSO Case Research

A VSO needs to research PTSD eligibility:

```bash
# Research regulations
python query_cli.py "What are the stressor requirements for PTSD?" --top-k 5

# Check procedures
python query_cli.py "How should VSOs document PTSD stressor evidence?" --top-k 5

# Find precedents
python query_cli.py "What BVA cases address PTSD stressor credibility?" --top-k 10
```

### Scenario 2: Veteran Self-Service

A veteran wants to understand their benefits:

```bash
# Basic eligibility
python query_cli.py "Am I eligible for PTSD benefits from Iraq service?"

# Rating process
python query_cli.py "How is PTSD rated by the VA?"

# Appeal process
python query_cli.py "What can I do if my PTSD claim is denied?"
```

### Scenario 3: Legal Research

An attorney researching a complex case:

```python
# Complex multi-part query
questions = [
    "What is the legal standard for secondary service connection?",
    "How does aggravation differ from secondary connection?",
    "What evidence is needed for secondary PTSD claims?"
]

for question in questions:
    result = rag.query(question, top_k=10)
    print(f"\nQ: {question}")
    print(f"A: {result['response'][:200]}...")
    print(f"Sources: {[c.source for c in result['citations'][:3]]}")
```

## Performance Tips

### 1. Optimize Retrieval

```python
# Use fewer results for simple queries
result = rag.query("What is PTSD?", top_k=3)

# Use more for complex research
result = rag.query(
    "Compare service connection requirements across all conditions",
    top_k=15
)
```

### 2. Batch Operations

```python
# Batch ingest documents
from pathlib import Path
from app.services.ingest import get_ingestor

ingestor = get_ingestor()
pdf_files = Path("data/raw").glob("*.pdf")

for pdf_file in pdf_files:
    result = ingestor.ingest_pdf(pdf_file, "CFR")
    print(f"Processed: {pdf_file.name}")
```

### 3. Caching Responses

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_query(query: str) -> str:
    result = rag.query(query)
    return result['response']

# Repeated queries hit cache
answer1 = cached_query("What is PTSD?")
answer2 = cached_query("What is PTSD?")  # From cache
```

## Error Handling

### Example: Robust Query Handler

```python
def safe_query(query: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            result = rag.query(query)
            return result
        except Exception as e:
            if attempt == max_retries - 1:
                return {
                    "response": "I apologize, but I encountered an error. Please try again.",
                    "citations": [],
                    "error": str(e)
                }
            time.sleep(2 ** attempt)  # Exponential backoff
```

## Integration Examples

### Slack Bot

```python
from slack_bolt import App

app = App(token=os.environ["SLACK_BOT_TOKEN"])

@app.message("va-assist")
def handle_va_query(message, say):
    query = message['text'].replace('va-assist', '').strip()
    result = rag.query(query)
    
    say({
        "text": result['response'],
        "attachments": [
            {
                "title": f"Citation {i+1}: {c.source}",
                "text": c.content[:100] + "..."
            }
            for i, c in enumerate(result['citations'][:3])
        ]
    })
```

### Discord Bot

```python
import discord

client = discord.Client()

@client.event
async def on_message(message):
    if message.content.startswith('!va'):
        query = message.content[3:].strip()
        result = rag.query(query)
        
        embed = discord.Embed(
            title="VA Claims Assistant",
            description=result['response']
        )
        
        for citation in result['citations'][:3]:
            embed.add_field(
                name=citation.source,
                value=f"Relevance: {citation.relevance_score:.0%}",
                inline=True
            )
        
        await message.channel.send(embed=embed)
```

---

For more examples, see the test suite in `tests/` directory.
