# Valor Assist - Quick Start Guide

This guide will help you get Valor Assist up and running in 5 minutes.

## Prerequisites

- Python 3.11 or higher
- Anthropic API key ([get one here](https://console.anthropic.com/))
- Voyage AI API key ([get one here](https://www.voyageai.com/))

## Installation

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/genregod/Claude-vet-AI-.git
cd Claude-vet-AI-

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
# ANTHROPIC_API_KEY=sk-ant-...
# VOYAGE_API_KEY=pa-...
```

### 3. Start the Server

```bash
# Start FastAPI server
python -m uvicorn app.main:app --reload
```

The server will start at `http://localhost:8000`

## Quick Usage Examples

### 1. View API Documentation

Open your browser to:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 2. Check Health

```bash
curl http://localhost:8000/api/v1/health
```

### 3. Ingest a Document

Using the CLI:
```bash
python ingest_cli.py /path/to/38_CFR_Part_3.pdf \
  --type CFR \
  --part "Part 3"
```

Using the API:
```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -F "file=@/path/to/38_CFR_Part_3.pdf" \
  -F "source_type=CFR" \
  -F "part=Part 3"
```

### 4. Query the System

Using the CLI:
```bash
python query_cli.py "What are the requirements for PTSD disability claims?"
```

Using the API:
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the requirements for PTSD disability claims?",
    "include_citations": true
  }'
```

## Docker Quick Start

### Using Docker Compose

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

The API will be available at `http://localhost:8000`

## Example Workflow

### Complete Example: PTSD Claims Assistant

```bash
# 1. Start the server (in one terminal)
python -m uvicorn app.main:app --reload

# 2. Ingest VA regulations (in another terminal)
python ingest_cli.py data/raw/38_CFR_Part_3.pdf --type CFR --part "Part 3"
python ingest_cli.py data/raw/M21-1_PTSD.pdf --type M21-1 --chapter "Chapter 4"

# 3. Query the system
python query_cli.py "What medical evidence is needed for PTSD claims?"

# 4. Get detailed citation
python query_cli.py "What is 38 CFR 3.304(f)?" --top-k 3
```

## Troubleshooting

### API Keys Not Found

Make sure you've:
1. Created a `.env` file (not just `.env.example`)
2. Added your actual API keys
3. Restarted the server after adding keys

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### ChromaDB Issues

```bash
# Remove existing database and restart
rm -rf chroma_db/
python -m uvicorn app.main:app --reload
```

## Next Steps

1. **Read the full README**: See `README.md` for comprehensive documentation
2. **Explore the API**: Visit `/docs` for interactive API documentation
3. **Add more documents**: Ingest M21-1 manuals and BVA decisions
4. **Customize**: Modify prompts in `app/services/rag.py` for your use case

## Getting Help

- Check the [README](README.md) for detailed documentation
- View API docs at `/docs` when server is running
- Open an issue on GitHub for bugs or questions

## What's Next?

After getting started, you might want to:

- **Customize the RAG pipeline**: Edit `app/services/rag.py`
- **Add new document types**: Extend `app/services/ingest.py`
- **Deploy to production**: See deployment section in README
- **Add authentication**: Implement auth middleware
- **Build a frontend**: Use the API to create a web or mobile app

---

**Happy coding!** 🎖️
