"""
Configuration management for Valor Assist.
Loads settings from environment variables with validation.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )
    
    # API Keys
    anthropic_api_key: str
    voyage_api_key: str
    
    # Application Settings
    app_name: str = "Valor Assist"
    app_version: str = "1.0.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    
    # ChromaDB Configuration
    chroma_db_path: str = "./chroma_db"
    chroma_collection_name: str = "va_legal_docs"
    
    # RAG Configuration
    embedding_model: str = "voyage-law-2"
    llm_model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 4096
    temperature: float = 0.0
    top_k_results: int = 5
    
    # PDF Processing
    pdf_max_size_mb: int = 50
    chunk_size: int = 1000
    chunk_overlap: int = 200


# Global settings instance
settings = Settings()
