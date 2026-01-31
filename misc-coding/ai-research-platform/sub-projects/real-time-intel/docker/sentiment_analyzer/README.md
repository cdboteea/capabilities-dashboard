# Sentiment Analyzer Service

Enhanced financial sentiment analysis service with machine learning models and financial context awareness.

## 🎯 **Features**

- **Financial-Tuned Models**: Uses FinBERT for financial text sentiment analysis
- **Enhanced Lexicon**: Custom financial terminology weighting and sector-specific adjustments
- **Emotion Detection**: VADER sentiment analysis for emotional context
- **Entity-Aware Analysis**: Sentiment analysis for specific financial entities (tickers, companies)
- **Background Processing**: Async task queue for batch processing
- **Real-time API**: FastAPI with WebSocket support for streaming analysis
- **Monitoring**: Prometheus metrics and structured logging
- **Production Ready**: Docker containerized with health checks

## 🚀 **Quick Start**

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/db"
export SENTIMENT_MODEL_NAME="ProsusAI/finbert"

# Run the service
uvicorn src.main:app --reload --port 8304
```

### Docker

```bash
# Build and run
docker-compose up sentiment-analyzer

# Or build directly
docker build -t sentiment-analyzer .
docker run -p 8304:8304 sentiment-analyzer
```

## 📡 **API Endpoints**

### Core Analysis

- `POST /v1/analyze/text` - Analyze single text
- `POST /v1/analyze/batch` - Analyze multiple texts
- `POST /v1/analyze/event` - Analyze event (background processing)
- `POST /v1/analyze/batch-background` - Batch analysis (background)

### Task Management

- `GET /v1/tasks/{task_id}` - Get task status
- `GET /v1/tasks` - Get queue status

### Database Queries

- `GET /v1/sentiment/{event_id}` - Get event sentiment
- `GET /v1/sentiment/search` - Search sentiment data

### Monitoring

- `GET /v1/health` - Health check
- `GET /v1/status` - Service status
- `GET /v1/metrics` - Prometheus metrics

### Admin

- `POST /v1/admin/cleanup-tasks` - Clean old tasks
- `GET /v1/admin/stats` - Service statistics

## 🔧 **Configuration**

### Environment Variables

```env
# Service
SENTIMENT_ANALYZER_PORT=8304
DATABASE_URL=postgresql://user:pass@host:5432/db

# Models
SENTIMENT_MODEL_NAME=ProsusAI/finbert
MAX_BATCH_SIZE=16
MODEL_CACHE_DIR=/app/models

# Processing
BACKGROUND_WORKERS=2
TASK_CLEANUP_HOURS=24

# Performance
TORCH_DEVICE=cpu
TRANSFORMERS_CACHE=/app/models/transformers
```

### Model Configuration

The service uses FinBERT (ProsusAI/finbert) by default for financial sentiment analysis. You can configure:

- **Model Selection**: Change `SENTIMENT_MODEL_NAME` to use different models
- **Batch Size**: Adjust `MAX_BATCH_SIZE` based on available memory
- **Device**: Set `TORCH_DEVICE` to `cuda` for GPU acceleration (if available)

## 📊 **Analysis Features**

### Financial Context

- **Lexicon Weighting**: 100+ financial terms with sentiment weights
- **Sector Multipliers**: Technology (1.1x), Financials (1.2x), Utilities (0.8x), etc.
- **Entity Extraction**: Automatic ticker and company name detection

### Emotion Detection

Detects financial emotions:
- **Fear**: panic, worry, anxiety, uncertainty
- **Greed**: euphoria, FOMO, speculation
- **Confidence**: bullish, assured, optimistic
- **Disappointment**: bearish, frustrated, concerned

### Output Format

```json
{
  "overall": {
    "score": 0.65,
    "confidence": 0.89
  },
  "financial": {
    "score": 0.72,
    "confidence": 0.89
  },
  "emotions": {
    "confidence": {"score": 0.8, "confidence": 0.7},
    "positive": {"score": 0.6, "confidence": 0.8}
  },
  "entities": [
    {
      "entity": "AAPL",
      "sentiment": {"score": 0.7, "confidence": 0.85}
    }
  ]
}
```

## 🔄 **Background Processing**

The service supports background task processing for:

- **Event Analysis**: Process events from Event Processor
- **Batch Processing**: Handle large text batches asynchronously
- **Database Persistence**: Save results to PostgreSQL

### Task Status Tracking

```bash
# Submit background task
curl -X POST "http://localhost:8304/v1/analyze/batch-background" \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Great earnings!", "Disappointing results"]}'

# Check task status
curl "http://localhost:8304/v1/tasks/{task_id}"
```

## 📈 **Monitoring**

### Health Checks

```bash
# Basic health
curl http://localhost:8304/v1/health

# Detailed status
curl http://localhost:8304/v1/status
```

### Prometheus Metrics

Available at `/v1/metrics`:

- `sentiment_requests_total` - Total API requests
- `sentiment_request_duration_seconds` - Request latency
- `sentiment_analysis_total` - Total analyses performed
- `sentiment_analysis_duration_seconds` - Analysis duration

### Logging

Structured JSON logging with:
- Request/response logging
- Error tracking
- Performance metrics
- Background task status

## 🧪 **Testing**

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_sentiment_engine.py

# Run with coverage
pytest --cov=src tests/
```

### Test Categories

- **Unit Tests**: Core sentiment engine functionality
- **API Tests**: FastAPI endpoint testing
- **Integration Tests**: Database and external service integration
- **Performance Tests**: Load testing and benchmarks

## 🔗 **Integration**

### Event Processor Integration

The service integrates with the Event Processor (Port 8303) to provide sentiment analysis for incoming events:

```python
# Event Processor calls
POST /v1/analyze/event
{
  "event_id": "event-123",
  "text": "Apple reports strong Q4 earnings",
  "entities": ["AAPL"],
  "sector": "technology"
}
```

### Database Schema

Sentiment results are stored in the `sentiment_scores` table:

```sql
CREATE TABLE sentiment_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL,
    overall_score FLOAT NOT NULL,
    overall_confidence FLOAT NOT NULL,
    financial_score FLOAT,
    financial_confidence FLOAT,
    emotions JSONB,
    entities JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 🚀 **Performance**

### Benchmarks

- **Single Analysis**: ~200ms average (CPU)
- **Batch Processing**: ~50ms per text (batch of 16)
- **Memory Usage**: ~2GB base + ~500MB per worker
- **Throughput**: ~200 analyses/minute (2 workers)

### Optimization Tips

1. **GPU Acceleration**: Set `TORCH_DEVICE=cuda` if available
2. **Batch Size**: Increase `MAX_BATCH_SIZE` for higher throughput
3. **Workers**: Scale `BACKGROUND_WORKERS` based on CPU cores
4. **Model Caching**: Use persistent volume for `/app/models`

## 📝 **Development**

### Project Structure

```
sentiment_analyzer/
├── src/
│   ├── main.py                 # FastAPI application
│   ├── config.py              # Configuration settings
│   ├── models/                # Pydantic models
│   ├── processors/            # Sentiment analysis logic
│   ├── services/              # Background tasks
│   └── utils/                 # Database utilities
├── tests/                     # Test suite
├── config/                    # Configuration files
├── Dockerfile                 # Container definition
└── requirements.txt           # Python dependencies
```

### Adding New Features

1. **New Models**: Add model loading in `processors/sentiment_engine.py`
2. **Custom Lexicons**: Extend `processors/financial_lexicon.py`
3. **API Endpoints**: Add routes in `main.py`
4. **Background Tasks**: Extend `services/background_tasks.py`

## 🔧 **Troubleshooting**

### Common Issues

1. **Model Download Failures**
   ```bash
   # Pre-download models
   python -c "from transformers import AutoModel; AutoModel.from_pretrained('ProsusAI/finbert')"
   ```

2. **Memory Issues**
   ```bash
   # Reduce batch size
   export MAX_BATCH_SIZE=8
   ```

3. **Database Connection**
   ```bash
   # Test connection
   curl http://localhost:8304/v1/status
   ```

### Logs

```bash
# View service logs
docker logs real_time_intel_sentiment_analyzer

# Follow logs
docker logs -f real_time_intel_sentiment_analyzer
```

## 📄 **License**

Part of the AI Research Platform - Real-Time Intel system.

---

**Service Status**: ✅ Production Ready  
**Version**: 1.0.0  
**Port**: 8304  
**Dependencies**: PostgreSQL, Event Processor  
**Resources**: 6GB RAM, 3 CPU cores 