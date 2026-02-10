"""
Test suite for Valor Assist API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint returns API information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Valor Assist"
    assert "endpoints" in data


def test_health_endpoint():
    """Test the health check endpoint."""
    with patch('app.api.endpoints.get_ingestor') as mock_ingestor:
        # Mock the ingestor
        mock_instance = Mock()
        mock_instance.get_collection_stats.return_value = {
            "total_chunks": 100,
            "collection_name": "va_legal_docs"
        }
        mock_ingestor.return_value = mock_instance
        
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


def test_chat_endpoint_structure():
    """Test chat endpoint accepts proper request structure."""
    # Mock RAG pipeline
    with patch('app.api.endpoints.get_rag_pipeline') as mock_rag:
        mock_instance = Mock()
        mock_instance.query.return_value = {
            "response": "Test response",
            "citations": [],
            "chunks_retrieved": 0
        }
        mock_rag.return_value = mock_instance
        
        request_data = {
            "query": "What is the process for filing a VA disability claim?",
            "conversation_history": [],
            "include_citations": True
        }
        
        response = client.post("/api/v1/chat", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "citations" in data
        assert "timestamp" in data


def test_chat_endpoint_validation():
    """Test chat endpoint validates empty queries."""
    request_data = {
        "query": "",
        "include_citations": True
    }
    
    response = client.post("/api/v1/chat", json=request_data)
    assert response.status_code == 422  # Validation error


def test_stats_endpoint():
    """Test stats endpoint."""
    with patch('app.api.endpoints.get_ingestor') as mock_ingestor:
        mock_instance = Mock()
        mock_instance.get_collection_stats.return_value = {
            "total_chunks": 100,
            "collection_name": "va_legal_docs",
            "embedding_model": "voyage-law-2"
        }
        mock_ingestor.return_value = mock_instance
        
        response = client.get("/api/v1/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_chunks" in data
        assert "collection_name" in data
