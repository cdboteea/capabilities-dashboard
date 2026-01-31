"""Unit tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from src.main import app
from src.models.sentiment_models import SentimentScore, SentimentResult


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_sentiment_result():
    """Mock sentiment analysis result."""
    return SentimentResult(
        overall=SentimentScore(score=0.5, confidence=0.8),
        financial=SentimentScore(score=0.6, confidence=0.8),
        emotions={"positive": SentimentScore(score=0.7, confidence=0.8)},
        entities=None
    )


class TestHealthEndpoints:
    """Test health and monitoring endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "sentiment-analyzer"
        assert "timestamp" in data


class TestSentimentAnalysisEndpoints:
    """Test sentiment analysis endpoints."""
    
    def test_analyze_text_success(self, client, mock_sentiment_result):
        """Test successful text analysis."""
        with patch("src.main.get_engine") as mock_engine:
            mock_engine.return_value.analyze = AsyncMock(return_value=mock_sentiment_result)
            
            response = client.post(
                "/v1/analyze/text",
                json={"text": "This is great news!"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert len(data["results"]) == 1
    
    def test_analyze_batch_success(self, client, mock_sentiment_result):
        """Test successful batch analysis."""
        with patch("src.main.get_engine") as mock_engine:
            mock_engine.return_value.analyze_batch = AsyncMock(
                return_value=[mock_sentiment_result, mock_sentiment_result]
            )
            
            response = client.post(
                "/v1/analyze/batch",
                json={
                    "texts": ["Great news!", "Bad news!"],
                    "entities": ["AAPL"]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert len(data["results"]) == 2


if __name__ == "__main__":
    pytest.main([__file__])
