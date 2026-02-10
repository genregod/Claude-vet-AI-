# Valor Assist - VA Claims AI for Army Veterans

A production-grade FastAPI backend implementing a RAG (Retrieval-Augmented Generation) pipeline for VA disability claims assistance. Built with Claude-3-5-Sonnet and Voyage-law-2 embeddings, specialized for Army veterans navigating the VA benefits system.

## 🎯 Features

- **RAG Pipeline**: Semantic search over VA legal documents (38 CFR, M21-1, BVA decisions)
- **Claude-3-5-Sonnet**: Advanced reasoning with XML-tagged prompts for strict legal citations
- **Voyage-law-2 Embeddings**: Specialized legal document embeddings for precise retrieval
- **ChromaDB Vector Store**: Efficient storage and retrieval of document embeddings
- **Modular Architecture**: Clean separation of concerns (ingest, RAG, API)
- **PDF Processing**: Robust cleaning and extraction from various PDF formats
- **Metadata Tagging**: Rich metadata for sources, sections, and citations
- **RESTful API**: FastAPI with automatic documentation

## 🏗️ Architecture

```
Valor Assist Architecture
│
├── FastAPI Application (app/main.py)
│   └── API Endpoints (app/api/endpoints.py)
│       ├── /chat - Query interface with Claude
│       ├── /ingest - Document ingestion
│       ├── /health - System health check
│       └── /stats - Knowledge base statistics
│
├── RAG Pipeline (app/services/rag.py)
│   ├── Voyage-law-2 embeddings for queries
│   ├── ChromaDB semantic search
│   └── Claude-3-5-Sonnet response generation
│
├── Document Ingestion (app/services/ingest.py)
│   ├── PDF processing and cleaning
│   ├── Text chunking with legal awareness
│   ├── Voyage-law-2 embeddings for documents
│   └── ChromaDB storage
│
└── Utilities
    ├── PDF Processor (app/utils/pdf_processor.py)
    └── Text Chunker (app/utils/text_chunker.py)
```

## 📁 Project Structure

```
Claude-vet-AI-/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints.py         # API routes
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py            # Configuration management
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py           # Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ingest.py            # Document ingestion
│   │   └── rag.py               # RAG pipeline
│   └── utils/
│       ├── __init__.py
│       ├── pdf_processor.py     # PDF cleaning
│       └── text_chunker.py      # Text chunking
├── data/
│   ├── raw/                     # Source PDFs
│   └── processed/               # Processed documents
├── tests/
│   ├── __init__.py
│   └── test_api.py             # API tests
├── chroma_db/                   # ChromaDB storage (auto-created)
├── .env.example                 # Environment variables template
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key (for Claude)
- Voyage AI API key (for embeddings)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/genregod/Claude-vet-AI-.git
cd Claude-vet-AI-
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys:
# ANTHROPIC_API_KEY=your_key_here
# VOYAGE_API_KEY=your_key_here
```

5. **Run the application**
```bash
python -m uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

## 📚 API Usage

### Interactive Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Chat Endpoint

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the requirements for PTSD disability claims?",
    "include_citations": true
  }'
```

Response:
```json
{
  "response": "Based on 38 CFR 3.304(f), PTSD disability claims require...",
  "citations": [
    {
      "source": "38 CFR Part 3",
      "section": "§ 3.304",
      "content": "Service connection for PTSD requires...",
      "relevance_score": 0.92,
      "metadata": {...}
    }
  ],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Document Ingestion

```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -F "file=@38_CFR_Part_3.pdf" \
  -F "source_type=CFR" \
  -F "part=Part 3"
```

### Health Check

```bash
curl "http://localhost:8000/api/v1/health"
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | Required |
| `VOYAGE_API_KEY` | Voyage AI API key | Required |
| `CHROMA_DB_PATH` | Path to ChromaDB storage | `./chroma_db` |
| `EMBEDDING_MODEL` | Voyage embedding model | `voyage-law-2` |
| `LLM_MODEL` | Claude model version | `claude-3-5-sonnet-20241022` |
| `MAX_TOKENS` | Max tokens for responses | `4096` |
| `TEMPERATURE` | LLM temperature | `0.0` |
| `TOP_K_RESULTS` | Number of retrieval results | `5` |
| `CHUNK_SIZE` | Text chunk size | `1000` |
| `CHUNK_OVERLAP` | Chunk overlap | `200` |

## 📖 Document Types

### 38 CFR (Code of Federal Regulations)
Federal regulations governing VA benefits. Key parts:
- **Part 3**: Adjudication (eligibility, ratings)
- **Part 4**: Schedule for Rating Disabilities

### M21-1 Adjudication Procedures Manual
VA's internal manual for processing claims.

### BVA Decisions
Board of Veterans' Appeals precedent decisions.

## 🧪 Testing

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## 🔒 Security Considerations

- Never commit `.env` file with real API keys
- Use environment-specific configurations
- Implement rate limiting for production
- Restrict CORS origins in production
- Validate and sanitize all inputs
- Implement authentication/authorization for production use

## 🛠️ Development

### Code Style
```bash
# Format code
black app/ tests/

# Lint
flake8 app/ tests/

# Type checking
mypy app/
```

### Adding New Document Sources

1. Add extraction logic in `app/utils/pdf_processor.py`
2. Create ingestion method in `app/services/ingest.py`
3. Update metadata schema in `app/models/schemas.py`
4. Add endpoint parameter in `app/api/endpoints.py`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Built for Army veterans navigating VA disability claims
- Powered by Anthropic's Claude-3-5-Sonnet
- Embeddings by Voyage AI's voyage-law-2
- Vector storage by ChromaDB

## 📧 Support

For issues and questions:
- GitHub Issues: [Issues](https://github.com/genregod/Claude-vet-AI-/issues)
- Documentation: See `/docs` endpoint

## 🗺️ Roadmap

- [ ] Conversation history management
- [ ] Multi-user support with authentication
- [ ] Advanced filtering by document type/date
- [ ] Batch document ingestion
- [ ] Export citations to various formats
- [ ] Integration with VSO platforms
- [ ] Mobile API endpoints
- [ ] Real-time chat interface

---

**Note**: This system provides information from official VA sources but is not a substitute for professional legal or medical advice. Veterans should consult with accredited VSOs or attorneys for personalized assistance. 
