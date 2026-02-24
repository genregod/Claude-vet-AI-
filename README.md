# Valor Assist — AI Veterans Claims Assistant

An AI-powered assistant that helps U.S. military veterans navigate VA disability
claims, appeals, and 38 CFR regulations. Built with **FastAPI** (Python) on the
backend and **Vite/React** (TypeScript) on the frontend, using Claude 3.5 Sonnet
and a Retrieval-Augmented Generation (RAG) pipeline grounded in real legal texts.

---

## Project Structure

```
.
├── app/                        # FastAPI backend
│   ├── server.py               # App entry point — all endpoints
│   ├── config.py               # Settings (pydantic-settings, reads .env)
│   ├── rag_chain.py            # RAG: retrieve → prompt → Claude
│   ├── prompts.py              # System prompts and quick actions
│   ├── vector_store.py         # ChromaDB + embeddings
│   ├── ingest.py               # Document ingestion / chunking
│   ├── sessions.py             # Encrypted session management
│   ├── auth.py / auth_routes.py # ID.me + VA OAuth
│   ├── claim_routes.py         # Claim submission routes
│   ├── claims_evaluator.py     # AI claim evaluation
│   ├── records_extractor.py    # Military records extraction
│   ├── middleware.py           # CORS, rate limiting, security headers
│   ├── pii_shield.py           # PII redaction
│   ├── va_integration.py       # VA.gov Lighthouse API client
│   └── data/
│       ├── raw/                # Legal source documents (.txt, .md)
│       ├── chroma_db/          # ChromaDB storage (gitignored)
│       └── uploads/            # Veteran uploads (gitignored)
├── frontend/                   # Vite + React (TypeScript) frontend
│   ├── src/
│   │   ├── main.tsx            # App entry point
│   │   ├── App.tsx             # Root component + router
│   │   ├── pages/              # Route-level page components
│   │   ├── components/         # Shared UI components (shadcn/ui)
│   │   ├── lib/                # API client, query client, utilities
│   │   └── hooks/              # Custom React hooks
│   ├── package.json
│   └── vite.config.js
├── docs/
│   └── references/             # Reference PDFs (Docker, VA Dev API)
├── scripts/
│   └── run_ingest.py           # Standalone knowledge-base ingestion
├── infrastructure/
│   └── aws-architecture.md     # AWS production deployment guide
├── .devcontainer/
│   └── devcontainer.json       # GitHub Codespaces / VS Code Dev Container
├── Dockerfile                  # Backend production image
├── frontend/Dockerfile         # Frontend production image (nginx)
├── docker-compose.yml          # Full-stack local development
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Python tool config (ruff)
└── .env.example                # Environment variable template
```

---

## Quick Start — Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- An **Anthropic API key** — set as `ANTHROPIC_API_KEY`

### 1. Clone and configure environment

```bash
cp .env.example .env
# Edit .env — at minimum set ANTHROPIC_API_KEY
```

### 2. Backend (FastAPI)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Optional: ingest knowledge base documents
python -m scripts.run_ingest

# Start the API server
uvicorn app.server:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

### 3. Frontend (Vite / React)

```bash
cd frontend
npm install
npm run dev
# App: http://localhost:5173
```

---

## Docker Compose (full stack)

Run the entire stack (backend + frontend nginx) with a single command:

```bash
# Copy and fill in your .env first
cp .env.example .env

docker-compose up --build
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000/docs
```

---

## GitHub Codespaces

This repo ships with a `.devcontainer` configuration that installs Python 3.11
and Node 20, forwards ports 8000 / 5173 / 3000, and runs post-create installs
automatically.

### Required Codespaces Secret

Set the following in your repository / Codespaces settings
(**Settings → Secrets and variables → Codespaces**):

| Secret name         | Description                           |
|---------------------|---------------------------------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (required)     |
| `VOYAGE_API_KEY`    | Voyage AI key (optional, embeddings)  |

Codespaces automatically injects these as environment variables; no `.env` file
is needed when running in Codespaces.

### Start services inside Codespaces

```bash
# Terminal 1 — Backend
uvicorn app.server:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev -- --port 5173
```

---

## API Overview

| Method | Path                  | Description                        |
|--------|-----------------------|------------------------------------|
| `GET`  | `/health`             | Liveness probe                     |
| `GET`  | `/stats`              | System statistics                  |
| `POST` | `/chat/session`       | Create an encrypted session        |
| `POST` | `/chat`               | Multi-turn Q&A (RAG + Claude)      |
| `POST` | `/chat/quick-action`  | Pre-built expert queries           |
| `POST` | `/evaluate`           | Free case evaluation               |
| `POST` | `/upload`             | Veteran document upload            |
| `POST` | `/ingest`             | Admin: re-ingest knowledge base    |
| `POST` | `/auth/idme/login`    | ID.me OAuth login                  |
| `POST` | `/claims/start`       | Start a new VA claim               |

Full interactive docs available at `http://localhost:8000/docs` when running locally.

---

## Environment Variables

See `.env.example` for all available configuration options.

| Variable             | Required | Description                                    |
|----------------------|----------|------------------------------------------------|
| `ANTHROPIC_API_KEY`  | ✅       | Claude API key                                 |
| `VOYAGE_API_KEY`     | ❌       | Voyage AI key (if `EMBEDDING_PROVIDER=voyageai`) |
| `EMBEDDING_PROVIDER` | ❌       | `voyageai` (default) or `huggingface`          |
| `ENCRYPTION_KEY`     | ❌       | Fernet key for session encryption              |
| `JWT_SECRET_KEY`     | ❌       | JWT signing secret                             |
| `IDME_CLIENT_ID`     | ❌       | ID.me OAuth client ID                          |
| `IDME_CLIENT_SECRET` | ❌       | ID.me OAuth client secret                      |
| `VA_API_KEY`         | ❌       | VA.gov Lighthouse API key                      |

---

## Security

- **PII Redaction** — SSNs, VA file numbers, phone numbers, DOBs, emails are stripped at ingest time
- **Session Encryption** — Conversation history encrypted at rest (Fernet / AES-128-CBC)
- **CORS** — Configurable allowed origins
- **Rate Limiting** — Per-IP sliding window (default: 30 requests/minute)
- **Security Headers** — HSTS, X-Frame-Options, X-Content-Type-Options, CSP
- **File Upload Validation** — Extension whitelist + size limits

---

## Reference Documents

Reference PDFs are stored under `docs/references/`:

- [`docs/references/dckr.pdf`](docs/references/dckr.pdf) — Docker reference
- [`docs/references/vadevapi.pdf`](docs/references/vadevapi.pdf) — VA Developer API reference

---

## AWS Deployment

See [`infrastructure/aws-architecture.md`](infrastructure/aws-architecture.md) for the full production
architecture (ECS Fargate, DynamoDB sessions, S3 document storage, WAF, CloudFront).

### GitHub Actions AWS OIDC setup for CI/CD deploy

To allow the `.github/workflows/ci-cd.yml` pipeline to build, push, and deploy to AWS,
configure an IAM role trust for GitHub OIDC and use that role in the workflow.

This repository is configured to assume:

- GitHub **Repository Secret**: `AWS_ROLE_TO_ASSUME`
  - Example value from your setup:
    - `arn:aws:iam::<account-id>:role/github-actions-deployment-role`
  - Replace `<account-id>` with your 12-digit AWS account ID.
- GitHub **Repository Variable**: `ECS_TASK_EXECUTION_ROLE_ARN`
  - Example value:
    - `arn:aws:iam::<account-id>:role/ecsTaskExecutionRole`
- Optional GitHub **Repository Variables** (if you do not want default VPC auto-discovery):
  - `ECS_SUBNET_IDS` (comma-separated subnet IDs)
  - `ECS_SECURITY_GROUP_ID`

Configure `AWS_ROLE_TO_ASSUME` under **Settings → Secrets and variables → Actions → Secrets**.
You can keep optional ECS values under **Actions → Variables**.

No long-lived `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` are required in GitHub secrets.

The IAM role must be allowed to:
- Authenticate to ECR and push images to:
  - `valor-assist-backend`
  - `valor-assist-frontend`
- Update and wait on ECS services:
  - cluster `valor-assist-cluster`
  - services `valor-assist-backend` and `valor-assist-frontend`

The pipeline will now automatically create missing AWS deployment resources when possible:
- ECR repositories (`valor-assist-backend`, `valor-assist-frontend`)
- ECS cluster (`valor-assist-cluster`)
- ECS services (`valor-assist-backend`, `valor-assist-frontend`) using default VPC/subnets/security group

By default, ECS services are created with `assignPublicIp=ENABLED` in the CI workflow.
Set `ECS_ASSIGN_PUBLIC_IP` in `.github/workflows/ci-cd.yml` to `DISABLED` if your deployment uses private subnets/NAT.

Ensure your deployment region and names match `.github/workflows/ci-cd.yml` (defaults to `us-east-1`).
