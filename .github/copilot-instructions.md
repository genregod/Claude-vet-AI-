# Valor Assist — AI Coding Agent Guide

## Architecture Overview

**Valor Assist** is a full-stack RAG-powered VA disability claims assistant combining React + TypeScript + FastAPI + Claude 3.5 Sonnet + ChromaDB.

```
User → React SPA (Vite/TypeScript) → FastAPI → RAG Chain → [ChromaDB → Claude 3.5] → Cited Answer
```

**Tech Stack:**
- **Frontend**: React 18 + TypeScript + Vite + Wouter + TanStack Query + shadcn/ui (49 components) + Tailwind CSS v4
- **Backend**: FastAPI + Python 3.11 + Anthropic SDK + ChromaDB
- **Database**: PostgreSQL (AWS RDS) + ChromaDB (vector store)
- **Infrastructure**: Docker + GitHub Codespaces (dev) + AWS ECS Fargate (prod) + GitHub Actions (CI/CD)
- **AI**: Claude 3.5 Sonnet (RAG-powered legal analysis)

Key components:
- **Backend**: [app/server.py](../app/server.py) — FastAPI with `/chat`, `/evaluate`, `/upload`, `/health` endpoints
- **RAG Pipeline**: [app/rag_chain.py](../app/rag_chain.py) — retrieve → prompt assembly → Claude API call (direct SDK, no LangChain)
- **Vector Store**: [app/vector_store.py](../app/vector_store.py) — ChromaDB with VoyageAI voyage-law-2 or HuggingFace embeddings
- **Prompts**: [app/prompts.py](../app/prompts.py) — XML-tagged system prompts per Anthropic best practices
- **Security**: [app/pii_shield.py](../app/pii_shield.py) — centralized PII protection (encryption, log scrubbing, audit trail)
- **Frontend**: [frontend/src/App.tsx](../frontend/src/App.tsx) — React SPA with Wouter routing, shadcn/ui components
- **UI Components**: [frontend/src/components/](../frontend/src/components/) — 49+ reusable components (forms, chat, cards, dialogs)

## Critical Patterns

### 1. XML-Tagged Prompts (Anthropic Claude Convention)
All Claude prompts use structured XML tags for clarity and reliability:
```xml
<role>You are "Valor Assist"...</role>
<rules>1. CITATION REQUIREMENT — cite sources inline...</rules>
<context>{retrieved_chunks}</context>
```
See [app/prompts.py](../app/prompts.py) for templates. **Always maintain this structure when editing prompts**.

### 2. React + TypeScript Frontend Architecture
**Router**: Wouter (lightweight, ~1.2KB) instead of React Router
**State**: TanStack Query for server state, React hooks for local state
**Styling**: Tailwind CSS v4 with custom design system (navy #001c3d, gold #C5A55A)
**Components**: shadcn/ui (Radix UI primitives) for accessible, composable components

**Key files**:
- [frontend/src/App.tsx](../frontend/src/App.tsx) — Root component with Wouter routing
- [frontend/src/lib/queryClient.ts](../frontend/src/lib/queryClient.ts) — TanStack Query configuration + API wrapper
- [frontend/src/components/SimpleChatWindow.tsx](../frontend/src/components/SimpleChatWindow.tsx) — AI chat interface
- [frontend/src/components/ClaimForm.tsx](../frontend/src/components/ClaimForm.tsx) — Multi-step claim evaluation form

**API Integration Pattern**:
```typescript
// All API calls go through /api proxy -> FastAPI backend
const response = await apiRequest("POST", "/chat", {
  question: userMessage,
  session_id: sessionId
});
const data = await response.json();
```

### 3. PII Shield — Security-First Pattern  
Every piece of PII flows through [app/pii_shield.py](../app/pii_shield.py):
- **Encryption at rest**: Fernet (AES-128-CBC) for all sensitive fields
- **Log scrubbing**: Auto-redacts SSN, emails, VA file numbers from logs (installed at app startup)
- **Data classification**: `DataClass` enum defines PII/PHI/PFI/CREDENTIAL levels
- **Audit trail**: Logs all PII access with `audit_pii_access()`

When adding features handling user data, check `DataClass` mappings and use `scrub_pii_from_text()` for logs.

### 4. Document Ingestion Workflow
Legal documents in `app/data/raw/` → chunked → embedded → stored in ChromaDB.

**Source type auto-tagging** uses filename conventions ([app/ingest.py](../app/ingest.py)):
- `38_cfr*.txt` → tagged `38_CFR`
- `m21-1*.txt` → tagged `M21-1_Manual`
- `bva_decision*.txt` → tagged `BVA_Decision`

**Chunking strategy**: Word-based (not character-based) at ~400 words with 50-word overlap to preserve regulation context boundaries.

Run ingestion: `python -m scripts.run_ingest` or `POST /ingest` (admin endpoint).

### 5. Session Management
[app/sessions.py](../app/sessions.py) provides **encrypted in-memory sessions** for multi-turn chat:
- Each chat widget gets a unique `session_id` (UUID)
- Messages encrypted with Fernet before storage
- Auto-expires after `session_ttl_seconds` (default 1 hour)
- History capped at `max_conversation_turns * 2` to prevent unbounded growth
- **AWS migration path**: Swap `_sessions` dict for DynamoDB backend (see comments in code)

## Development Workflows

### Start Development Server (GitHub Codespaces)
```bash
# Backend (FastAPI)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.server  # http://localhost:8000

# Frontend (React + Vite) - separate terminal
cd frontend
npm install
npm run dev  # http://localhost:3000
```

### Full Stack with Docker
```bash
docker-compose up --build  # Frontend: http://localhost:3000, Backend: http://localhost:8000
```

### Re-ingest Documents After Changes
```bash
python -m scripts.run_ingest
```
Clears ChromaDB collection and rebuilds from `app/data/raw/`.

### Test RAG Pipeline
Interactive API docs at `http://localhost:8000/docs`:
1. `POST /chat/session` → get `session_id`
2. `POST /chat` with question + session_id → see cited answer + sources

### Environment Configuration
Required in `.env`:
- `ANTHROPIC_API_KEY` — Claude API access
- `ENCRYPTION_KEY` — Fernet key (generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)

Optional:
- `VOYAGE_API_KEY` — voyage-law-2 embeddings (otherwise falls back to HuggingFace)
- `VITE_API_URL` — Backend URL for frontend proxy (default: `http://localhost:8000`)

## Frontend Structure (React + TypeScript + Vite)

```
frontend/
├── src/
│   ├── App.tsx                 # Root component with Wouter routing
│   ├── main.tsx                # React app entry point
│   ├── index.css               # Tailwind CSS + custom design tokens
│   ├── components/             # All React components
│   │   ├── ui/                 # 49 shadcn/ui primitives (Button, Card, Dialog, etc.)
│   │   ├── Hero.tsx            # Landing page hero section
│   │   ├── Services.tsx        # Services showcase
│   │   ├── HowItWorks.tsx      # Process steps
│   │   ├── Testimonials.tsx    # Testimonials carousel
│   │   ├── Demo.tsx            # Interactive demo section
│   │   ├── CTA.tsx             # Call-to-action sections
│   │   ├── Header.tsx          # Navigation header
│   │   ├── Footer.tsx          # Site footer
│   │   ├── SimpleChatWindow.tsx # AI chat widget
│   │   └── ClaimForm.tsx       # Multi-step claim form
│   ├── pages/                  # Page-level components
│   │   ├── HomePage.tsx        # Landing page assembly
│   │   ├── ChatPage.tsx        # Dedicated chat page
│   │   ├── EvaluatePage.tsx    # Case evaluation page
│   │   ├── HealthCheck.tsx     # System health status
│   │   └── NotFound.tsx        # 404 page
│   ├── lib/                    # Utilities
│   │   ├── queryClient.ts      # TanStack Query + API wrapper
│   │   └── utils.ts            # Utility functions (cn, formatDate, etc.)
│   └── hooks/                  # Custom React hooks
│       └── use-toast.ts        # Toast notification system
├── vite.config.js              # Vite config with path aliases + proxy
├── tsconfig.json               # TypeScript configuration
├── tailwind.config.ts          # Tailwind CSS configuration
├── postcss.config.js           # PostCSS for Tailwind
├── components.json             # shadcn/ui configuration
└── package.json                # Dependencies + scripts
```

Build: `npm run build` → outputs to `frontend/dist/` (served by nginx in Docker).

## Integration Points

### Anthropic Claude API
[app/rag_chain.py](../app/rag_chain.py) uses the official `anthropic` Python SDK directly (not LangChain):
```python
response = self._client.messages.create(
    model=settings.claude_model,
    system=system_prompt,
    messages=conversation_history + [{"role": "user", "content": question}],
    max_tokens=settings.claude_max_tokens,
    temperature=settings.claude_temperature,
)
```
Keep low temperature (0.2) for factual legal analysis.

### ChromaDB + Embeddings
[app/vector_store.py](../app/vector_store.py):
- **Primary embedding**: VoyageAI voyage-law-2 (legal-optimized, requires API key)
- **Fallback**: HuggingFace sentence-transformers/all-MiniLM-L6-v2 (local, no API)
- Collection name: `"valor_assist"` (configurable via `settings.chroma_collection_name`)
- Storage: `app/data/chroma_db/` (gitignored persistent directory)

### Frontend-Backend Communication
Frontend uses Vite proxy in dev, nginx proxy in production:
```javascript
// vite.config.js
proxy: {
  '/api': {
    target: process.env.VITE_API_URL || 'http://localhost:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ''),
  },
}
```

All frontend API calls:
```typescript
// /api/chat → proxied to → backend:8000/chat
await apiRequest("POST", "/chat", { question, session_id });
```

## AWS Production Architecture

See [infrastructure/aws-architecture.md](../infrastructure/aws-architecture.md) for full deployment guide:
- **Compute**: ECS Fargate (2 vCPU / 4 GB RAM per task)
- **Storage**: S3 for documents + EFS for ChromaDB, DynamoDB for sessions (future)
- **Security**: AWS WAF + Secrets Manager + KMS encryption + VPC private subnets
- **Monitoring**: CloudWatch Logs + X-Ray tracing for Anthropic API latency
- **CI/CD**: GitHub Actions → ECR → ECS (see [.github/workflows/ci-cd.yml](../.github/workflows/ci-cd.yml))

## Common Tasks

### Add a new API endpoint
1. Define route handler in [app/server.py](../app/server.py) with Pydantic models
2. Add corresponding API call in [frontend/src/lib/queryClient.ts](../frontend/src/lib/queryClient.ts) or page component
3. Test via `/docs` (FastAPI Swagger UI)

### Add a new React component
1. Create component in [frontend/src/components/](../frontend/src/components/)
2. Use shadcn/ui primitives from `@/components/ui/`
3. Style with Tailwind CSS classes (navy, gold design tokens)
4. Import and use in page components

### Add a new page
1. Create page component in [frontend/src/pages/](../frontend/src/pages/)
2. Add route in [frontend/src/App.tsx](../frontend/src/App.tsx):
   ```tsx
   <Route path="/new-page" component={NewPage} />
   ```

### Add a new legal document source type
1. Add filename pattern rule to `_SOURCE_TAG_RULES` in [app/ingest.py](../app/ingest.py)
2. Update `QUICK_ACTION_QUERIES` in [app/prompts.py](../app/prompts.py) if needed
3. Re-run ingestion: `python -m scripts.run_ingest`

### Modify prompt behavior
Edit [app/prompts.py](../app/prompts.py) — preserve XML structure. Test with `/chat` endpoint before deploying.

### Add PII protection for new field
1. Add field pattern to `SENSITIVE_FIELD_PATTERNS` dict in [app/pii_shield.py](../app/pii_shield.py)
2. Classify as PII/PHI/PFI using `DataClass` enum
3. Log scrubber auto-updates; verify with test log output

## Key Files Reference

| File | Purpose |
|------|---------|
| [frontend/src/App.tsx](../frontend/src/App.tsx) | React root component, Wouter routing, error boundary |
| [frontend/src/lib/queryClient.ts](../frontend/src/lib/queryClient.ts) | TanStack Query config + `apiRequest()` wrapper |
| [frontend/src/components/SimpleChatWindow.tsx](../frontend/src/components/SimpleChatWindow.tsx) | AI chat widget with session management |
| [app/server.py](../app/server.py) | FastAPI app, all HTTP endpoints, lifespan management |
| [app/rag_chain.py](../app/rag_chain.py) | RAG orchestration (retrieve → prompt → Claude) |
| [app/prompts.py](../app/prompts.py) | XML-tagged system prompts for Claude |
| [app/vector_store.py](../app/vector_store.py) | ChromaDB wrapper + embedding logic |
| [app/ingest.py](../app/ingest.py) | Document chunking, PII cleaning, source-type tagging |
| [app/sessions.py](../app/sessions.py) | Encrypted conversation session store |
| [app/pii_shield.py](../app/pii_shield.py) | Centralized PII encryption + log scrubbing |
| [app/config.py](../app/config.py) | Pydantic settings (API keys, timeout, chunking params) |
| [scripts/run_ingest.py](../scripts/run_ingest.py) | Standalone ingestion runner |
| [docker-compose.yml](../docker-compose.yml) | Full-stack local dev (backend + frontend + volumes) |
| [.github/workflows/ci-cd.yml](../.github/workflows/ci-cd.yml) | GitHub Actions CI/CD to AWS ECS |

## Testing Notes

**Backend**: Manual testing via FastAPI `/docs` UI
**Frontend**: Manual testing in browser + TypeScript type checking (`npm run check`)

To test end-to-end RAG:
1. Add test document to `app/data/raw/test_doc.txt`
2. Run ingestion: `python -m scripts.run_ingest`
3. Open chat widget, ask question related to test document
4. Verify cited sources match retrieved chunks in response

For PII scrubbing verification, check logs for redacted patterns (should show `[REDACTED-PII]`).

## Mobile-Responsive Design

All components use Tailwind CSS responsive breakpoints:
- **Tailwind breakpoints**: `sm:`, `md:`, `lg:`, `xl:`, `2xl:`
- **Mobile-first approach**: Base styles for mobile, enhance for larger screens
- **Touch-friendly**: Minimum 44x44px tap targets for mobile
- **Responsive navigation**: Header collapses to hamburger menu on mobile

Test responsive: Use browser DevTools device emulation for iOS/Android viewports.


```
User Question → FastAPI → RAG Chain → [Retrieve from ChromaDB → Build XML Prompt → Claude API] → Cited Answer
```

Key components:
- **Backend**: [app/server.py](../app/server.py) — FastAPI with `/chat`, `/evaluate`, `/upload` endpoints
- **RAG Pipeline**: [app/rag_chain.py](../app/rag_chain.py) — retrieve → prompt assembly → Claude API call (direct SDK, no LangChain)
- **Vector Store**: [app/vector_store.py](../app/vector_store.py) — ChromaDB with VoyageAI voyage-law-2 or HuggingFace embeddings
- **Prompts**: [app/prompts.py](../app/prompts.py) — XML-tagged system prompts per Anthropic best practices
- **Security**: [app/pii_shield.py](../app/pii_shield.py) — centralized PII protection (encryption, log scrubbing, audit trail)

## Critical Patterns

### 1. XML-Tagged Prompts (Anthropic Claude Convention)
All Claude prompts use structured XML tags for clarity and reliability:
```xml
<role>You are "Valor Assist"...</role>
<rules>1. CITATION REQUIREMENT — cite sources inline...</rules>
<context>{retrieved_chunks}</context>
```
See [app/prompts.py](../app/prompts.py) for templates. **Always maintain this structure when editing prompts**.

### 2. PII Shield — Security-First Pattern
Every piece of PII flows through [app/pii_shield.py](../app/pii_shield.py):
- **Encryption at rest**: Fernet (AES-128-CBC) for all sensitive fields
- **Log scrubbing**: Auto-redacts SSN, emails, VA file numbers from logs (installed at app startup)
- **Data classification**: `DataClass` enum defines PII/PHI/PFI/CREDENTIAL levels
- **Audit trail**: Logs all PII access with `audit_pii_access()`

When adding features handling user data, check `DataClass` mappings and use `scrub_pii_from_text()` for logs.

### 3. Document Ingestion Workflow
Legal documents in `app/data/raw/` → chunked → embedded → stored in ChromaDB.

**Source type auto-tagging** uses filename conventions ([app/ingest.py](../app/ingest.py)):
- `38_cfr*.txt` → tagged `38_CFR`
- `m21-1*.txt` → tagged `M21-1_Manual`
- `bva_decision*.txt` → tagged `BVA_Decision`

**Chunking strategy**: Word-based (not character-based) at ~400 words with 50-word overlap to preserve regulation context boundaries.

Run ingestion: `python -m scripts.run_ingest` or `POST /ingest` (admin endpoint).

### 4. Session Management
[app/sessions.py](../app/sessions.py) provides **encrypted in-memory sessions** for multi-turn chat:
- Each chat widget gets a unique `session_id` (UUID)
- Messages encrypted with Fernet before storage
- Auto-expires after `session_ttl_seconds` (default 1 hour)
- History capped at `max_conversation_turns * 2` to prevent unbounded growth
- **AWS migration path**: Swap `_sessions` dict for DynamoDB backend (see comments in code)

### 5. Authentication Flow (Optional ID.me + VA.gov)
[app/auth_routes.py](../app/auth_routes.py) implements multi-tier verification:
- **Tier 1**: Email/password (basic)
- **Tier 2**: ID.me OAuth (LOA3 identity proofing)
- **Tier 3**: VA.gov Lighthouse API (veteran status confirmation)

Protected endpoints use `@require_consent` decorator to enforce consent acknowledgment.

## Development Workflows

### Start Development Server
```bash
# Virtual environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.server  # http://localhost:8000/docs

# Docker (full stack with React frontend)
docker-compose up --build  # http://localhost:3000
```

### Re-ingest Documents After Changes
```bash
python -m scripts.run_ingest
```
Clears ChromaDB collection and rebuilds from `app/data/raw/`.

### Test RAG Pipeline
Interactive API docs at `http://localhost:8000/docs`:
1. `POST /chat/session` → get `session_id`
2. `POST /chat` with question + session_id → see cited answer + sources

### Environment Configuration
Required in `.env`:
- `ANTHROPIC_API_KEY` — Claude API access
- `ENCRYPTION_KEY` — Fernet key (generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)

Optional: `VOYAGE_API_KEY` for voyage-law-2 embeddings (otherwise falls back to HuggingFace).

## Frontend Structure (React + Vite)

- [frontend/src/App.jsx](../frontend/src/App.jsx) — React Router with `/`, `/login`, `/consent`, `/evaluate` routes
- [frontend/src/pages/ChatPage.jsx](../frontend/src/pages/ChatPage.jsx) — Chat widget with quick action buttons
- [frontend/src/pages/EvaluatePage.jsx](../frontend/src/pages/EvaluatePage.jsx) — Case intake form
- [frontend/src/api.js](../frontend/src/api.js) — Axios wrapper for backend API calls

Build: `cd frontend && npm run build` → outputs to `frontend/dist/` (served by nginx in Docker).

## Integration Points

### Anthropic Claude API
[app/rag_chain.py](../app/rag_chain.py) uses the official `anthropic` Python SDK directly (not LangChain):
```python
response = self._client.messages.create(
    model=settings.claude_model,
    system=system_prompt,
    messages=conversation_history + [{"role": "user", "content": question}],
    max_tokens=settings.claude_max_tokens,
    temperature=settings.claude_temperature,
)
```
Keep low temperature (0.2) for factual legal analysis.

### ChromaDB + Embeddings
[app/vector_store.py](../app/vector_store.py):
- **Primary embedding**: VoyageAI voyage-law-2 (legal-optimized, requires API key)
- **Fallback**: HuggingFace sentence-transformers/all-MiniLM-L6-v2 (local, no API)
- Collection name: `"valor_assist"` (configurable via `settings.chroma_collection_name`)
- Storage: `app/data/chroma_db/` (gitignored persistent directory)

### VA.gov Lighthouse API
[app/va_integration.py](../app/va_integration.py) queries veteran status, disability ratings, and claims. Requires:
- OAuth consent flow (redirects user to VA.gov)
- LOA3 identity proofing (typically via ID.me first)
- Sandbox vs. production endpoints controlled by `settings.va_api_sandbox`

## AWS Production Architecture

See [infrastructure/aws-architecture.md](../infrastructure/aws-architecture.md) for full deployment guide:
- **Compute**: ECS Fargate (2 vCPU / 4 GB RAM per task)
- **Storage**: S3 for documents + EFS for ChromaDB, DynamoDB for sessions
- **Security**: AWS WAF + Secrets Manager + KMS encryption + VPC private subnets
- **Monitoring**: CloudWatch Logs + X-Ray tracing for Anthropic API latency

## Common Tasks

### Add a new endpoint
1. Define Pydantic models in [app/server.py](../app/server.py)
2. Add route handler with appropriate decorators (`@require_consent` if protected)
3. Update [frontend/src/api.js](../frontend/src/api.js) with corresponding client function

### Add a new legal document source type
1. Add filename pattern rule to `_SOURCE_TAG_RULES` in [app/ingest.py](../app/ingest.py)
2. Update `QUICK_ACTION_QUERIES` in [app/prompts.py](../app/prompts.py) if needed for quick actions
3. Re-run ingestion: `python -m scripts.run_ingest`

### Modify prompt behavior
Edit [app/prompts.py](../app/prompts.py) — preserve XML structure. Test with `/chat` endpoint before deploying.

### Add PII protection for new field
1. Add field pattern to `SENSITIVE_FIELD_PATTERNS` dict in [app/pii_shield.py](../app/pii_shield.py)
2. Classify as PII/PHI/PFI using `DataClass` enum
3. Log scrubber auto-updates; verify with test log output

## Key Files Reference

| File | Purpose |
|------|---------|
| [app/server.py](../app/server.py) | FastAPI app, all HTTP endpoints, lifespan management |
| [app/rag_chain.py](../app/rag_chain.py) | RAG orchestration (retrieve → prompt → Claude) |
| [app/prompts.py](../app/prompts.py) | XML-tagged system prompts for Claude |
| [app/vector_store.py](../app/vector_store.py) | ChromaDB wrapper + embedding logic |
| [app/ingest.py](../app/ingest.py) | Document chunking, PII cleaning, source-type tagging |
| [app/sessions.py](../app/sessions.py) | Encrypted conversation session store |
| [app/pii_shield.py](../app/pii_shield.py) | Centralized PII encryption + log scrubbing |
| [app/config.py](../app/config.py) | Pydantic settings (API keys, timeout, chunking params) |
| [scripts/run_ingest.py](../scripts/run_ingest.py) | Standalone ingestion runner |
| [docker-compose.yml](../docker-compose.yml) | Full-stack local dev (backend + frontend + volumes) |

## Testing Notes

No formal test suite yet. Manual testing workflow:
1. Add test document to `app/data/raw/test_doc.txt`
2. Run ingestion: `python -m scripts.run_ingest`
3. Query via `/docs` interactive UI or `curl`
4. Check [app/data/chroma_db/](../app/data/chroma_db/) was updated
5. Verify cited sources match retrieved chunks

For PII scrubbing verification, check logs for redacted patterns (should show `[REDACTED-PII]`).
