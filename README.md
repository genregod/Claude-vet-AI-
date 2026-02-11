# Valor Assist — AI Veterans Claims Assistant

An AI-powered application that helps U.S. military veterans navigate VA disability
claims, appeals, and 38 CFR regulations. Built with FastAPI, Claude 3.5 Sonnet,
and a Retrieval-Augmented Generation (RAG) pipeline grounded in real legal texts.

## Important Disclaimer

**Valor Assist is for informational and educational purposes only.** This application:
- Does NOT replace an accredited Veterans Service Officer (VSO) or attorney
- Does NOT file claims on your behalf
- Does NOT provide legal advice
- Should be used as a supplementary research tool

Always consult with an accredited VSO or attorney for official VA claims representation.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (React / Next.js)                                     │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────────┐ │
│  │ Chat     │  │ Quick Action │  │ Free Case Evaluation Form │ │
│  │ Widget   │  │ Buttons      │  │ (Branch / Rating / Issue) │ │
│  └────┬─────┘  └──────┬───────┘  └────────────┬──────────────┘ │
└───────┼────────────────┼───────────────────────┼────────────────┘
        │                │                       │
        ▼                ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI Server (app/server.py)                                 │
│                                                                 │
│  POST /chat              ← multi-turn Q&A                       │
│  POST /chat/quick-action ← pre-built expert queries             │
│  POST /chat/session      ← create encrypted session             │
│  POST /evaluate          ← case intake evaluation               │
│  POST /upload            ← veteran document upload              │
│  POST /ingest            ← admin: re-ingest knowledge base      │
│  GET  /health            ← liveness probe                       │
│  GET  /stats             ← system statistics                    │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Sessions    │  │ Rate Limiter │  │ CORS + Security Headers│ │
│  │ (Fernet    │  │ (per-IP)     │  │ (HSTS, XSS, CSP)      │ │
│  │  encrypted) │  │              │  │                        │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  RAG Chain (app/rag_chain.py)                                   │
│                                                                 │
│  1. Semantic search → ChromaDB (top-k relevant chunks)          │
│  2. Context assembly → XML-tagged system prompt                 │
│  3. Claude 3.5 Sonnet → cited, empathetic answer                │
│                                                                 │
│  ┌──────────────┐          ┌──────────────────────────────────┐ │
│  │ Vector Store │          │ Anthropic API (Claude 3.5 Sonnet)│ │
│  │ (ChromaDB)   │          │ system prompt uses <role>,       │ │
│  │              │          │ <rules>, <context>, <format>     │ │
│  └──────┬───────┘          └──────────────────────────────────┘ │
│         │                                                       │
│  ┌──────┴───────────────────────────────────────────────────┐   │
│  │ Embeddings: Voyage AI voyage-law-2 OR HuggingFace        │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Knowledge Base (app/data/raw/)                                 │
│                                                                 │
│  Source Types:                                                  │
│  • 38_CFR          — Title 38 Code of Federal Regulations       │
│  • M21-1_Manual    — VA Adjudication Procedures Manual          │
│  • BVA_Decision    — Board of Veterans' Appeals decisions        │
│  • US_Code         — United States Code (Title 38)              │
│  • BCMR            — Board for Correction of Military Records   │
│  • DRB             — Discharge Review Board proceedings         │
│  • COVA            — Court of Appeals for Veterans Claims       │
│  • VA_Form         — VA form instructions and guidance          │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
app/
├── config.py              Settings (API keys, models, security, sessions)
├── server.py              FastAPI app — all endpoints
├── rag_chain.py           RAG orchestration (retrieve → prompt → Claude)
├── prompts.py             XML-tagged system prompts + quick actions
├── vector_store.py        Embedding + ChromaDB (Voyage AI / HuggingFace)
├── ingest.py              Document ingestion, chunking, metadata tagging
├── sessions.py            Encrypted conversation session management
├── middleware.py           CORS, rate limiting, security headers
├── utils/
│   └── text_cleaning.py   PII redaction, header/footer removal
└── data/
    ├── raw/               Legal source documents (.txt, .md)
    ├── chroma_db/         ChromaDB persistent storage (gitignored)
    └── uploads/           Veteran-uploaded documents (gitignored)

scripts/
└── run_ingest.py          Standalone ingestion runner

infrastructure/
└── aws-architecture.md    AWS production deployment guide
```

## Quick Start

### 1. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY (required)
```

### 3. Ingest the Knowledge Base

```bash
python -m scripts.run_ingest
```

This reads all documents from `app/data/raw/`, cleans them (PII redaction,
header removal), chunks them (~400 words with 50-word overlap), and stores
the embeddings in ChromaDB.

### 4. Start the Server

```bash
python -m app.server
# API docs: http://localhost:8000/docs
```

### 5. Docker

```bash
docker-compose up --build
```

## API Endpoints

### Chat Widget

```bash
# Create a session (for multi-turn conversation)
curl -X POST http://localhost:8000/chat/session

# Ask a question (with session for continuity)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How do I appeal a PTSD denial?",
    "session_id": "<session_id_from_above>"
  }'

# Quick action (chat widget buttons)
curl -X POST http://localhost:8000/chat/quick-action \
  -H "Content-Type: application/json" \
  -d '{"action": "learn_appeals", "session_id": "<session_id>"}'
```

### Case Evaluation Form

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "service_branch": "Army",
    "current_rating": "30%",
    "primary_concerns": "PTSD from combat deployment, tinnitus, and knee injury",
    "additional_details": "Deployed to Afghanistan 2012-2013. Previously denied for PTSD in 2019."
  }'
```

### Document Upload

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@my_medical_records.txt" \
  -F "source_type=General"
```

## Security

- **PII Redaction**: All ingested documents pass through automatic PII stripping
  (SSNs, VA file numbers, phone numbers, DOBs, emails)
- **Session Encryption**: Conversation history encrypted at rest with Fernet (AES-128-CBC)
- **CORS**: Configurable allowed origins (locked to your frontend domain in production)
- **Rate Limiting**: Per-IP sliding window (default: 30 requests/minute)
- **Security Headers**: HSTS, X-Frame-Options, X-Content-Type-Options, CSP
- **File Upload Validation**: Extension whitelist + size limits

## Adding Legal Documents

Place `.txt` or `.md` files in `app/data/raw/` using these naming conventions
for automatic source-type tagging:

| Filename contains | Tagged as       |
|-------------------|-----------------|
| `38_cfr`, `cfr`   | `38_CFR`        |
| `m21-1`, `m21`    | `M21-1_Manual`  |
| `bva`, `decision` | `BVA_Decision`  |
| `usc`, `us_code`  | `US_Code`       |
| `bcmr`            | `BCMR`          |
| `drb`             | `DRB`           |
| `cova`, `cavc`    | `COVA`          |
| `va_form`         | `VA_Form`       |
| *(anything else)*  | `General`       |

After adding files, run ingestion: `python -m scripts.run_ingest` or `POST /ingest`.

## VA Claims Resources

- [VA.gov - How to File a Claim](https://www.va.gov/disability/how-to-file-claim/)
- [VA.gov - Evidence Requirements](https://www.va.gov/disability/how-to-file-claim/evidence-needed/)
- [Find a VSO](https://www.va.gov/vso/)
- [VA Decision Review Options](https://www.va.gov/decision-reviews/)

## AWS Deployment

See `infrastructure/aws-architecture.md` for the full production architecture
(ECS Fargate, DynamoDB sessions, S3 document storage, WAF, CloudFront).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
