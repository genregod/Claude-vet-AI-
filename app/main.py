"""
Valor Assist - FastAPI Backend
VA Claims AI for Army Veterans

Main application entry point.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.endpoints import router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"ChromaDB path: {settings.chroma_db_path}")
    logger.info(f"Embedding model: {settings.embedding_model}")
    logger.info(f"LLM model: {settings.llm_model}")
    
    # Initialize services (singletons will be created on first use)
    from app.services.ingest import get_ingestor
    from app.services.rag import get_rag_pipeline
    
    try:
        # Pre-initialize services to catch configuration errors early
        ingestor = get_ingestor()
        rag = get_rag_pipeline()
        stats = ingestor.get_collection_stats()
        logger.info(f"Knowledge base initialized with {stats['total_chunks']} chunks")
    except Exception as e:
        logger.error(f"Error initializing services: {e}")
        logger.warning("Services will be initialized on first request")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="VA Claims AI Assistant for Army Veterans - RAG-powered legal assistance",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router, prefix="/api/v1", tags=["api"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "VA Claims AI Assistant for Army Veterans",
        "endpoints": {
            "chat": "/api/v1/chat",
            "ingest": "/api/v1/ingest",
            "health": "/api/v1/health",
            "stats": "/api/v1/stats",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
