"""
Valor Assist — Configuration

Centralizes all settings: API keys, model selection, chunking parameters,
vector DB paths, session management, security, and AWS deployment config.
Uses pydantic-settings so values can be overridden with environment
variables or a .env file.
"""

from pathlib import Path

from cryptography.fernet import Fernet
from pydantic_settings import BaseSettings


# ── Paths ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DOCS_DIR = DATA_DIR / "raw"
CHROMA_DIR = DATA_DIR / "chroma_db"
UPLOADS_DIR = DATA_DIR / "uploads"

# Ensure upload directory exists
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    """Runtime settings — override via env vars or .env file."""

    # ── Anthropic / Claude ───────────────────────────────────────────
    anthropic_api_key: str = ""
    claude_model: str = "claude-3-5-sonnet-latest"
    claude_max_tokens: int = 4096
    claude_temperature: float = 0.2  # low temp for factual legal analysis

    # ── Embeddings ───────────────────────────────────────────────────
    # Primary: Voyage AI voyage-law-2 (legal-optimized)
    # Fallback: HuggingFace sentence-transformers
    embedding_provider: str = "huggingface"  # "voyageai" or "huggingface"
    voyage_api_key: str = ""
    voyage_model: str = "voyage-law-2"
    hf_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── Chunking ─────────────────────────────────────────────────────
    chunk_size_words: int = 400          # target ~300-500 words per chunk
    chunk_overlap_words: int = 50        # overlap for context continuity

    # ── Retrieval ────────────────────────────────────────────────────
    retrieval_top_k: int = 5             # top-k chunks returned per query
    chroma_collection_name: str = "valor_assist"

    # ── Session Management ───────────────────────────────────────────
    # Fernet key for encrypting PII in session storage.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    encryption_key: str = Fernet.generate_key().decode()
    session_ttl_seconds: int = 3600      # 1 hour idle timeout
    max_conversation_turns: int = 20     # max turns kept in context window

    # ── Security / CORS ──────────────────────────────────────────────
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    rate_limit_max_requests: int = 30    # per window per IP
    rate_limit_window_seconds: int = 60
    enable_hsts: bool = False            # enable in production behind HTTPS
    max_upload_size_mb: int = 10

    # ── Server ───────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {
        "env_file": str(BASE_DIR.parent / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
