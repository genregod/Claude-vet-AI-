# Project Structure

## Directory Layout

```
Claude-vet-AI-/
│
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   │
│   ├── api/                      # API layer
│   │   ├── __init__.py
│   │   └── endpoints.py          # REST API endpoints
│   │
│   ├── core/                     # Core configuration
│   │   ├── __init__.py
│   │   └── config.py             # Settings and configuration
│   │
│   ├── models/                   # Data models
│   │   ├── __init__.py
│   │   └── schemas.py            # Pydantic request/response models
│   │
│   ├── services/                 # Business logic
│   │   ├── __init__.py
│   │   ├── ingest.py             # Document ingestion service
│   │   └── rag.py                # RAG pipeline service
│   │
│   └── utils/                    # Utilities
│       ├── __init__.py
│       ├── pdf_processor.py      # PDF extraction and cleaning
│       └── text_chunker.py       # Text chunking logic
│
├── data/                         # Data storage
│   ├── raw/                      # Raw source PDFs
│   │   └── .gitkeep
│   └── processed/                # Processed documents
│       └── .gitkeep
│
├── tests/                        # Test suite
│   ├── __init__.py
│   └── test_api.py               # API endpoint tests
│
├── chroma_db/                    # ChromaDB storage (auto-created)
│
├── .env                          # Environment variables (not committed)
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore rules
│
├── Dockerfile                    # Docker container definition
├── docker-compose.yml            # Docker Compose configuration
│
├── requirements.txt              # Python dependencies
│
├── ingest_cli.py                 # CLI for document ingestion
├── query_cli.py                  # CLI for querying
├── example_usage.py              # Usage examples
├── demo.py                       # Interactive demo
│
├── README.md                     # Main documentation
├── QUICKSTART.md                 # Quick start guide
├── EXAMPLES.md                   # Usage examples
└── PROJECT_STRUCTURE.md          # This file
```

## Module Descriptions

### `app/main.py`
FastAPI application initialization with:
- CORS middleware
- Lifespan events
- Router inclusion
- Logging configuration

### `app/api/endpoints.py`
REST API endpoints:
- `POST /api/v1/chat` - Question answering with citations
- `POST /api/v1/ingest` - Document upload and ingestion
- `GET /api/v1/health` - Health check
- `GET /api/v1/stats` - Knowledge base statistics
- `DELETE /api/v1/documents/{id}` - Document deletion

### `app/services/ingest.py`
Document ingestion pipeline:
- PDF validation and processing
- Text extraction and cleaning
- Semantic chunking
- Embedding generation (Voyage-law-2)
- ChromaDB storage
- Specialized methods for CFR, M21-1, BVA

### `app/services/rag.py`
RAG pipeline implementation:
- Query embedding (Voyage-law-2)
- Semantic search (ChromaDB)
- Context building with XML tags
- Response generation (Claude-3-5-Sonnet)
- Citation formatting

### `app/utils/pdf_processor.py`
PDF processing utilities:
- Multi-method extraction (PyPDF, pdfplumber, PyMuPDF)
- Text cleaning and normalization
- Metadata extraction
- Hyphenation repair
- Artifact removal

### `app/utils/text_chunker.py`
Legal document chunking:
- Semantic-aware chunking
- Legal section detection
- Metadata enrichment
- Configurable chunk size/overlap

### `app/models/schemas.py`
Pydantic models for:
- `ChatRequest/Response` - Chat interactions
- `IngestRequest/Response` - Document ingestion
- `Citation` - Legal citations
- `DocumentMetadata` - Document metadata
- `HealthResponse` - System health

### `app/core/config.py`
Configuration management:
- Environment variable loading
- Settings validation
- Default values
- Type checking

## Data Flow

### Ingestion Flow
```
PDF File
  ↓
PDF Processor (extract & clean)
  ↓
Text Chunker (semantic splitting)
  ↓
Voyage AI (embedding generation)
  ↓
ChromaDB (vector storage)
```

### Query Flow
```
User Query
  ↓
Voyage AI (query embedding)
  ↓
ChromaDB (semantic search)
  ↓
Context Builder (format chunks)
  ↓
Claude-3-5-Sonnet (generate response)
  ↓
Response with Citations
```

## Configuration Files

### `.env`
Runtime configuration:
- API keys (Anthropic, Voyage AI)
- Database settings
- Model parameters
- Application settings

### `requirements.txt`
Python dependencies:
- Web: FastAPI, Uvicorn
- AI: Anthropic, Voyage AI
- Database: ChromaDB
- PDF: PyPDF, pdfplumber, PyMuPDF
- Utilities: python-dotenv, requests
- Testing: pytest, httpx

### `docker-compose.yml`
Container orchestration:
- Service definition
- Volume mounts
- Port mappings
- Health checks

## CLI Tools

### `ingest_cli.py`
Command-line document ingestion:
```bash
python ingest_cli.py <file> --type CFR --part "Part 3"
```

### `query_cli.py`
Command-line querying:
```bash
python query_cli.py "Your question here"
```

### `example_usage.py`
Validation and examples:
- Configuration check
- Module imports
- Model validation
- Usage instructions

### `demo.py`
Interactive demonstration:
- Configuration display
- Model examples
- PDF processing
- API overview

## Testing

### `tests/test_api.py`
API endpoint tests:
- Root endpoint
- Health check
- Chat functionality
- Validation
- Statistics

Run with:
```bash
pytest tests/ -v
```

## Documentation

### `README.md`
Comprehensive documentation:
- Features and architecture
- Installation instructions
- API usage examples
- Configuration guide
- Development guidelines

### `QUICKSTART.md`
5-minute setup guide:
- Installation steps
- Basic usage
- Docker deployment
- Troubleshooting

### `EXAMPLES.md`
Detailed usage examples:
- Chat queries
- Document ingestion
- API integration
- Use case scenarios
- Performance tips

## Deployment

### Local Development
```bash
python -m uvicorn app.main:app --reload
```

### Docker
```bash
docker-compose up -d
```

### Production
- Configure environment variables
- Set up reverse proxy (nginx)
- Enable HTTPS
- Implement authentication
- Set up monitoring

## Security Considerations

1. **API Keys**: Never commit `.env` to version control
2. **Input Validation**: All inputs validated with Pydantic
3. **File Upload**: Filename sanitization prevents path traversal
4. **CORS**: Configure allowed origins for production
5. **Rate Limiting**: Implement for production use
6. **Authentication**: Add OAuth2/JWT for production

## Extensibility

### Adding Document Types
1. Add extraction logic to `pdf_processor.py`
2. Create ingestion method in `ingest.py`
3. Update metadata schema in `schemas.py`
4. Add endpoint parameter in `endpoints.py`

### Customizing Prompts
Edit `rag.py`:
- Modify `system_prompt` for different behavior
- Adjust `user_message` template
- Change XML tag structure

### Adding Endpoints
1. Define route in `endpoints.py`
2. Create Pydantic models in `schemas.py`
3. Implement business logic in `services/`
4. Add tests in `tests/`

## Dependencies Graph

```
app.main
├── app.api.endpoints
│   ├── app.services.rag
│   │   ├── voyageai
│   │   ├── chromadb
│   │   └── anthropic
│   ├── app.services.ingest
│   │   ├── app.utils.pdf_processor
│   │   ├── app.utils.text_chunker
│   │   ├── voyageai
│   │   └── chromadb
│   └── app.models.schemas
└── app.core.config
```

## Best Practices

1. **Code Organization**: Keep modules focused and single-purpose
2. **Error Handling**: Always log errors and return meaningful messages
3. **Type Hints**: Use type hints for better IDE support and validation
4. **Documentation**: Document complex logic and public APIs
5. **Testing**: Test critical paths and edge cases
6. **Logging**: Use structured logging for debugging
7. **Configuration**: Use environment variables for deployment flexibility

---

For more information, see:
- [README.md](README.md) - Full documentation
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- [EXAMPLES.md](EXAMPLES.md) - Usage examples
