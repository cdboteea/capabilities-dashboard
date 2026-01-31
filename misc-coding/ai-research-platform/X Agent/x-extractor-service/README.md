# X Post Content Extraction Service

A containerized microservice for extracting content from X (Twitter) posts, designed for seamless integration with Node.js/Python dashboard applications.

## Overview

This service provides a RESTful API for extracting comprehensive content information from X (Twitter) post URLs, including post text, author information, engagement metrics, embedded URLs, media attachments, and referenced documents.

## Features

- **RESTful API**: Clean HTTP endpoints for easy integration
- **Batch Processing**: Extract content from multiple posts simultaneously
- **Rate Limiting**: Built-in rate limiting to respect API constraints
- **Error Handling**: Comprehensive error handling and logging
- **Docker Support**: Full containerization with Docker and docker-compose
- **Health Monitoring**: Health check endpoints for monitoring
- **Structured Logging**: JSON-formatted logs for monitoring and debugging
- **CORS Support**: Cross-origin requests enabled for frontend integration

## Architecture

- **Language**: Python 3.11
- **Framework**: FastAPI for high-performance async API
- **Containerization**: Docker with multi-stage builds
- **Deployment**: Docker Compose for easy orchestration
- **Logging**: Structured logging with configurable formats
- **Rate Limiting**: In-memory rate limiting with Redis support

## Quick Start

### Prerequisites

- Docker and Docker Compose (recommended)
- Python 3.11+ (for local development)

### Using Docker (Recommended)

1. Clone or extract the service files
2. Build and run the service:

```bash
# Build the Docker image
docker build -t x-extractor-service .

# Run the service
docker run -p 3000:3000 x-extractor-service

# Or use docker-compose
docker-compose up
```

3. The service will be available at `http://localhost:3000`

### Local Development

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the service:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 3000
```

## API Documentation

### Base URL

```
http://localhost:3000
```

### Endpoints

#### Health Check

**GET** `/api/health`

Returns the service health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-09T12:00:00Z",
  "version": "1.0.0",
  "uptime": 3600.0
}
```

#### Extract Posts

**POST** `/api/extract`

Extracts content from X post URLs.

**Request Body:**
```json
{
  "urls": [
    "https://x.com/username/status/1234567890",
    "https://twitter.com/username/status/0987654321"
  ]
}
```

**Response:**
```json
{
  "success": true,
  "posts": [
    {
      "post_url": "https://x.com/username/status/1234567890",
      "post_id": "1234567890",
      "author": {
        "username": "username",
        "display_name": "Display Name",
        "profile_image_url": "https://...",
        "verified": false
      },
      "content": "Post content text",
      "timestamp": "2025-07-09T12:00:00Z",
      "engagement": {
        "likes": 100,
        "retweets": 50,
        "replies": 25,
        "quotes": 10
      },
      "urls": [
        {
          "display_url": "t.co/abc123",
          "expanded_url": "https://example.com/full-url",
          "title": "Page Title",
          "description": "Page description"
        }
      ],
      "media": [
        {
          "type": "image",
          "url": "https://pbs.twimg.com/media/...",
          "preview_url": "https://...",
          "alt_text": "Image description",
          "width": 1200,
          "height": 800
        }
      ],
      "referenced_documents": [
        {
          "url": "https://example.com/document.pdf",
          "type": "PDF",
          "title": "Document Title",
          "description": "Document description"
        }
      ],
      "hashtags": ["hashtag1", "hashtag2"],
      "mentions": ["user1", "user2"],
      "is_reply": false,
      "reply_to_post_id": null,
      "is_retweet": false,
      "original_post_id": null
    }
  ],
  "errors": []
}
```

#### Root Endpoint

**GET** `/`

Returns service information and available endpoints.

### Rate Limiting

The service implements rate limiting with the following default limits:

- **Requests**: 100 requests per hour per IP address
- **Headers**: Rate limit information is included in response headers:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `X-RateLimit-Reset`: Unix timestamp when the limit resets

### Error Handling

The service provides structured error responses:

```json
{
  "error": "Error message",
  "detail": "Detailed error information",
  "timestamp": "2025-07-09T12:00:00Z"
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request (invalid input)
- `422`: Unprocessable Entity (validation error)
- `429`: Too Many Requests (rate limit exceeded)
- `500`: Internal Server Error

## Configuration

### Environment Variables

The service can be configured using environment variables:

```bash
# Service Configuration
APP_NAME=X Post Content Extraction Service
APP_VERSION=1.0.0
DEBUG=false
HOST=0.0.0.0
PORT=3000

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600

# Request Configuration
REQUEST_TIMEOUT=30
MAX_CONCURRENT_REQUESTS=10

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Redis Configuration (optional)
REDIS_URL=redis://redis:6379/0
```

### Docker Environment

Create a `.env` file based on `.env.example` for Docker deployment:

```bash
cp .env.example .env
# Edit .env with your configuration
```

## Deployment

### Docker Deployment

#### Single Container

```bash
# Build the image
docker build -t x-extractor-service .

# Run the container
docker run -d \
  --name x-extractor \
  -p 3000:3000 \
  -e LOG_LEVEL=INFO \
  x-extractor-service
```

#### Docker Compose

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

#### With Redis (Optional)

To enable Redis for enhanced rate limiting:

```bash
# Start with Redis profile
docker-compose --profile with-redis up -d
```

### Production Deployment

For production deployment, consider:

1. **Reverse Proxy**: Use nginx or similar for SSL termination
2. **Load Balancing**: Deploy multiple instances behind a load balancer
3. **Monitoring**: Set up health check monitoring
4. **Logging**: Configure log aggregation (ELK stack, etc.)
5. **Security**: Implement API authentication if needed

### Kubernetes Deployment

Example Kubernetes deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: x-extractor-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: x-extractor-service
  template:
    metadata:
      labels:
        app: x-extractor-service
    spec:
      containers:
      - name: x-extractor-service
        image: x-extractor-service:latest
        ports:
        - containerPort: 3000
        env:
        - name: LOG_LEVEL
          value: "INFO"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: x-extractor-service
spec:
  selector:
    app: x-extractor-service
  ports:
  - port: 80
    targetPort: 3000
  type: LoadBalancer
```

## Integration Examples

### Node.js Integration

```javascript
const axios = require('axios');

class XExtractorClient {
  constructor(baseUrl = 'http://localhost:3000') {
    this.baseUrl = baseUrl;
  }

  async extractPosts(urls) {
    try {
      const response = await axios.post(`${this.baseUrl}/api/extract`, {
        urls: urls
      });
      return response.data;
    } catch (error) {
      console.error('Extraction failed:', error.response?.data || error.message);
      throw error;
    }
  }

  async healthCheck() {
    const response = await axios.get(`${this.baseUrl}/api/health`);
    return response.data;
  }
}

// Usage
const client = new XExtractorClient();
const result = await client.extractPosts([
  'https://x.com/username/status/1234567890'
]);
console.log(result.posts);
```

### Python Integration

```python
import httpx
import asyncio

class XExtractorClient:
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url

    async def extract_posts(self, urls: list) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/extract",
                json={"urls": urls}
            )
            response.raise_for_status()
            return response.json()

    async def health_check(self) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/health")
            response.raise_for_status()
            return response.json()

# Usage
async def main():
    client = XExtractorClient()
    result = await client.extract_posts([
        "https://x.com/username/status/1234567890"
    ])
    print(result["posts"])

asyncio.run(main())
```

### cURL Examples

```bash
# Health check
curl http://localhost:3000/api/health

# Extract single post
curl -X POST http://localhost:3000/api/extract \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://x.com/username/status/1234567890"]}'

# Extract multiple posts
curl -X POST http://localhost:3000/api/extract \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://x.com/user1/status/1234567890",
      "https://x.com/user2/status/0987654321"
    ]
  }'
```

## Development

### Project Structure

```
x-extractor-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── models.py            # Pydantic data models
│   ├── extractor.py         # Core extraction logic
│   ├── rate_limiter.py      # Rate limiting middleware
│   ├── error_handlers.py    # Error handling
│   └── logging_config.py    # Logging configuration
├── tests/
│   └── test_service.py      # Test suite
├── config/
├── docs/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .dockerignore
└── README.md
```

### Running Tests

```bash
# Run the test suite
python test_service.py

# Run with pytest (if installed)
pytest tests/
```

### Adding New Features

1. **New Endpoints**: Add to `app/main.py`
2. **Data Models**: Update `app/models.py`
3. **Extraction Logic**: Modify `app/extractor.py`
4. **Configuration**: Update `app/config.py`
5. **Tests**: Add tests to `tests/`

## Limitations and Considerations

### Content Extraction Limitations

Due to X/Twitter's restrictions on web scraping and API access:

1. **Limited Content**: Basic content extraction may not capture all post details
2. **Rate Limiting**: Aggressive rate limiting may be applied by X/Twitter
3. **Authentication**: Some content may require authentication
4. **Dynamic Content**: JavaScript-rendered content may not be accessible

### Recommendations

1. **Official API**: For production use, consider X/Twitter's official API
2. **Caching**: Implement caching to reduce repeated requests
3. **Monitoring**: Monitor for changes in X/Twitter's structure
4. **Fallback**: Implement fallback mechanisms for failed extractions

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check logs
docker-compose logs x-extractor-service

# Check port availability
netstat -tulpn | grep :3000
```

#### Rate Limiting Issues

```bash
# Check rate limit headers
curl -v http://localhost:3000/api/extract \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://x.com/test/status/123"]}'
```

#### Extraction Failures

```bash
# Check service logs
tail -f server.log

# Test with known working URL
curl -X POST http://localhost:3000/api/extract \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://x.com/elonmusk/status/1812258574049157405"]}'
```

### Debug Mode

Enable debug mode for development:

```bash
# Set environment variable
export DEBUG=true

# Or in docker-compose.yml
environment:
  - DEBUG=true
```

## Support and Contributing

### Reporting Issues

When reporting issues, please include:

1. Service version
2. Request/response examples
3. Error logs
4. Environment details

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

## License

This project is provided as-is for educational and development purposes. Please ensure compliance with X/Twitter's Terms of Service when using this service.

## Changelog

### Version 1.0.0

- Initial release
- RESTful API endpoints
- Docker containerization
- Rate limiting
- Error handling
- Structured logging
- Health monitoring
- Comprehensive documentation

