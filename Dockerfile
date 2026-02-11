# ── Valor Assist — Production Dockerfile ─────────────────────────────
# Multi-stage build: slim Python image for minimal attack surface.
#
# Build:  docker build -t valor-assist .
# Run:    docker run -p 8000:8000 --env-file .env valor-assist

FROM python:3.11-slim AS base

# Security: run as non-root user
RUN groupadd -r valoruser && useradd -r -g valoruser valoruser

WORKDIR /opt/valor-assist

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/
COPY scripts/ scripts/

# Create writable directories for data (mounted as volumes in production)
RUN mkdir -p app/data/raw app/data/chroma_db app/data/uploads \
    && chown -R valoruser:valoruser /opt/valor-assist

USER valoruser

# Expose the API port
EXPOSE 8000

# Health check for ECS / load balancer
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run the FastAPI server via uvicorn (no --reload in production)
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
