"""Unit tests for sentiment analysis engine."""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.processors.sentiment_engine import SentimentEngine, get_engine
from src.processors.financial_lexicon import (
    get_financial_sentiment_weight,
    detect_emotions,
    extract_financial_entities
)
from src.models.sentiment_models import SentimentScore, SentimentResult


class TestFinancialLexicon:
    """Test financial lexicon functions."""
    
    def test_financial_sentiment_weight_positive(self):
        """Test positive financial sentiment weighting."""
        text = "The company reported strong earnings and beat expectations with impressive growth."
        weight = get_financial_sentiment_weight(text)
        assert weight > 1.0, "Should have positive weight for positive financial terms"
    
    def test_financial_sentiment_weight_negative(self):
        """Test negative financial sentiment weighting."""
        text = "The company reported terrible losses and missed expectations with declining revenue."
        weight = get_financial_sentiment_weight(text)
        assert weight < 1.0, "Should have negative weight for negative financial terms"
    
    def test_financial_sentiment_weight_neutral(self):
        """Test neutral financial sentiment weighting."""
        text = "The company held a meeting to discuss quarterly results."
        weight = get_financial_sentiment_weight(text)
        assert weight == 1.0, "Should have neutral weight for neutral text"
    
    def test_sector_multiplier(self):
        """Test sector-specific multipliers."""
        text = "Strong performance this quarter"
        tech_weight = get_financial_sentiment_weight(text, "technology")
        utilities_weight = get_financial_sentiment_weight(text, "utilities")
        
        assert tech_weight > utilities_weight, "Technology should have higher sentiment sensitivity"
    
    def test_detect_emotions_fear(self):
        """Test fear emotion detection."""
        text = "Investors are panicking due to market uncertainty and fear of recession."
        emotions = detect_emotions(text)
        
        assert "fear" in emotions, "Should detect fear emotion"
        assert "uncertainty" in emotions, "Should detect uncertainty emotion"
    
    def test_detect_emotions_confidence(self):
        """Test confidence emotion detection."""
        text = "Investors are confident and bullish about the company's future prospects."
        emotions = detect_emotions(text)
        
        assert "confidence" in emotions, "Should detect confidence emotion"
    
    def test_extract_financial_entities(self):
        """Test financial entity extraction."""
        text = "AAPL stock price rose while MSFT declined. The DOW index remained stable."
        entities = extract_financial_entities(text)
        
        assert "AAPL" in entities, "Should extract AAPL ticker"
        assert "MSFT" in entities, "Should extract MSFT ticker"
        assert "DOW" in entities, "Should extract DOW ticker"
        assert "THE" not in entities, "Should filter out common words"


class TestSentimentEngine:
    """Test sentiment analysis engine."""
    
    @pytest.fixture
    def engine(self):
        """Create sentiment engine instance."""
        return SentimentEngine()
    
    @pytest.fixture
    def mock_sentiment_pipeline(self):
        """Mock sentiment analysis pipeline."""
        mock_pipe = Mock()
        mock_pipe.return_value = [[
            {"label": "negative", "score": 0.1},
            {"label": "neutral", "score": 0.2},
            {"label": "positive", "score": 0.7}
        ]]
        return mock_pipe
    
    @pytest.fixture
    def mock_vader_analyzer(self):
        """Mock VADER sentiment analyzer."""
        mock_analyzer = Mock()
        mock_analyzer.polarity_scores.return_value = {
            "compound": 0.5,
            "pos": 0.7,
            "neu": 0.2,
            "neg": 0.1
        }
        return mock_analyzer
    
    @pytest.mark.asyncio
    async def test_analyze_base_sentiment(self, engine, mock_sentiment_pipeline):
        """Test base sentiment analysis."""
        with patch.object(engine, '_sentiment_pipe', mock_sentiment_pipeline):
            result = await engine._analyze_base_sentiment("This is great news!")
            
            assert isinstance(result, SentimentScore)
            assert result.score > 0, "Should have positive sentiment score"
            assert 0 <= result.confidence <= 1, "Confidence should be between 0 and 1"
    
    @pytest.mark.asyncio
    async def test_analyze_financial_sentiment(self, engine, mock_sentiment_pipeline):
        """Test financial sentiment analysis with context."""
        with patch.object(engine, '_sentiment_pipe', mock_sentiment_pipeline):
            text = "The company reported strong earnings and beat expectations."
            result = await engine._analyze_financial_sentiment(text, "technology")
            
            assert isinstance(result, SentimentScore)
            assert result.score != 0, "Should have non-zero sentiment score"
    
    @pytest.mark.asyncio
    async def test_analyze_emotions(self, engine, mock_vader_analyzer):
        """Test emotion detection."""
        with patch.object(engine, '_vader_analyzer', mock_vader_analyzer):
            text = "Investors are excited about the bullish market trends."
            emotions = await engine._analyze_emotions(text)
            
            assert isinstance(emotions, dict)
            assert "positive" in emotions, "Should detect positive emotion"
            assert "excitement" in emotions, "Should detect excitement emotion"
    
    @pytest.mark.asyncio
    async def test_analyze_entity_sentiment(self, engine, mock_sentiment_pipeline):
        """Test entity-specific sentiment analysis."""
        with patch.object(engine, '_sentiment_pipe', mock_sentiment_pipeline):
            text = "AAPL performed well this quarter. MSFT also showed strong results."
            entities = ["AAPL", "MSFT"]
            
            results = await engine._analyze_entity_sentiment(text, entities)
            
            assert len(results) == 2, "Should analyze sentiment for both entities"
            assert all(r.entity in entities for r in results), "Should have correct entities"
    
    def test_extract_entity_context(self, engine):
        """Test entity context extraction."""
        text = "AAPL reported strong earnings. The company beat expectations. MSFT also performed well."
        
        context = engine._extract_entity_context(text, "AAPL", window_size=1)
        
        assert len(context) > 0, "Should extract context sentences"
        assert any("AAPL" in sentence for sentence in context), "Should include entity sentence"
    
    @pytest.mark.asyncio
    async def test_analyze_batch(self, engine):
        """Test batch sentiment analysis."""
        texts = [
            "Great news for the company!",
            "Disappointing quarterly results.",
            "Neutral market conditions."
        ]
        
        with patch.object(engine, 'analyze') as mock_analyze:
            mock_analyze.return_value = SentimentResult(
                overall=SentimentScore(score=0.5, confidence=0.8)
            )
            
            results = await engine.analyze_batch(texts)
            
            assert len(results) == len(texts), "Should analyze all texts"
            assert mock_analyze.call_count == len(texts), "Should call analyze for each text"
    
    @pytest.mark.asyncio
    async def test_full_analysis_integration(self, engine):
        """Test full sentiment analysis integration."""
        with patch.object(engine, '_load') as mock_load:
            with patch.object(engine, '_analyze_base_sentiment') as mock_base:
                with patch.object(engine, '_analyze_financial_sentiment') as mock_financial:
                    with patch.object(engine, '_analyze_emotions') as mock_emotions:
                        with patch.object(engine, '_analyze_entity_sentiment') as mock_entities:
                            
                            # Setup mocks
                            mock_base.return_value = SentimentScore(score=0.5, confidence=0.8)
                            mock_financial.return_value = SentimentScore(score=0.6, confidence=0.8)
                            mock_emotions.return_value = {"positive": SentimentScore(score=0.7, confidence=0.8)}
                            mock_entities.return_value = []
                            
                            # Test analysis
                            result = await engine.analyze("Test text", ["AAPL"], "technology")
                            
                            assert isinstance(result, SentimentResult)
                            assert result.overall is not None
                            assert result.financial is not None
                            assert result.emotions is not None


class TestSentimentEngineCache:
    """Test sentiment engine caching."""
    
    def test_get_engine_cache(self):
        """Test that get_engine returns cached instance."""
        engine1 = get_engine()
        engine2 = get_engine()
        
        assert engine1 is engine2, "Should return same cached instance"
    
    def test_engine_singleton(self):
        """Test sentiment engine singleton behavior."""
        engine = get_engine()
        
        assert isinstance(engine, SentimentEngine)
        assert hasattr(engine, '_lock')
        assert hasattr(engine, '_sentiment_pipe')
        assert hasattr(engine, '_vader_analyzer')


@pytest.mark.asyncio
async def test_concurrent_analysis():
    """Test concurrent sentiment analysis."""
    engine = get_engine()
    
    texts = [f"Test text {i}" for i in range(10)]
    
    with patch.object(engine, '_analyze_base_sentiment') as mock_analyze:
        mock_analyze.return_value = SentimentScore(score=0.5, confidence=0.8)
        
        # Run concurrent analyses
        tasks = [engine.analyze(text) for text in texts]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == len(texts), "Should handle concurrent requests"
        assert all(isinstance(r, SentimentResult) for r in results), "All results should be SentimentResult"


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in sentiment analysis."""
    engine = get_engine()
    
    with patch.object(engine, '_analyze_base_sentiment') as mock_analyze:
        mock_analyze.side_effect = Exception("Analysis failed")
        
        with pytest.raises(Exception, match="Analysis failed"):
            await engine.analyze("Test text")


def test_sentiment_score_validation():
    """Test sentiment score validation."""
    # Valid scores
    score1 = SentimentScore(score=0.5, confidence=0.8)
    assert score1.score == 0.5
    assert score1.confidence == 0.8
    
    # Edge cases
    score2 = SentimentScore(score=-1.0, confidence=0.0)
    assert score2.score == -1.0
    assert score2.confidence == 0.0
    
    score3 = SentimentScore(score=1.0, confidence=1.0)
    assert score3.score == 1.0
    assert score3.confidence == 1.0


if __name__ == "__main__":
    pytest.main([__file__]) 