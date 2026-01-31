# API Documentation

## X Post Content Extraction Service API

This document provides detailed information about the API endpoints, request/response formats, and usage examples.

## Base Information

- **Base URL**: `http://localhost:3000`
- **Content-Type**: `application/json`
- **Authentication**: None (public endpoints)
- **Rate Limiting**: 100 requests per hour per IP

## Endpoints

### 1. Health Check

Check the service health and status.

**Endpoint**: `GET /api/health`

**Parameters**: None

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-07-09T12:00:00.000000",
  "version": "1.0.0",
  "uptime": 3600.0
}
```

**Status Codes**:
- `200 OK`: Service is healthy
- `500 Internal Server Error`: Service is unhealthy

**Example**:
```bash
curl http://localhost:3000/api/health
```

### 2. Extract Posts

Extract content from X (Twitter) post URLs.

**Endpoint**: `POST /api/extract`

**Request Body**:
```json
{
  "urls": [
    "string"
  ]
}
```

**Parameters**:
- `urls` (array of strings, required): List of X/Twitter post URLs to extract content from
  - Maximum 50 URLs per request
  - Must be valid X.com or Twitter.com URLs
  - Must contain `/status/` in the URL path

**Response**:
```json
{
  "success": boolean,
  "posts": [
    {
      "post_url": "string",
      "post_id": "string",
      "author": {
        "username": "string",
        "display_name": "string",
        "profile_image_url": "string|null",
        "verified": boolean
      },
      "content": "string",
      "timestamp": "string (ISO 8601)",
      "engagement": {
        "likes": integer,
        "retweets": integer,
        "replies": integer,
        "quotes": integer
      },
      "urls": [
        {
          "display_url": "string",
          "expanded_url": "string",
          "title": "string|null",
          "description": "string|null"
        }
      ],
      "media": [
        {
          "type": "string",
          "url": "string",
          "preview_url": "string|null",
          "alt_text": "string|null",
          "width": "integer|null",
          "height": "integer|null"
        }
      ],
      "referenced_documents": [
        {
          "url": "string",
          "type": "string",
          "title": "string|null",
          "description": "string|null"
        }
      ],
      "hashtags": ["string"],
      "mentions": ["string"],
      "is_reply": boolean,
      "reply_to_post_id": "string|null",
      "is_retweet": boolean,
      "original_post_id": "string|null"
    }
  ],
  "errors": [
    {
      "url": "string",
      "error": "string",
      "timestamp": "string (ISO 8601)"
    }
  ]
}
```

**Status Codes**:
- `200 OK`: Request processed successfully (may contain errors for individual URLs)
- `400 Bad Request`: Invalid request format or parameters
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

**Examples**:

Single URL:
```bash
curl -X POST http://localhost:3000/api/extract \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://x.com/elonmusk/status/1812258574049157405"]
  }'
```

Multiple URLs:
```bash
curl -X POST http://localhost:3000/api/extract \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://x.com/user1/status/1234567890",
      "https://twitter.com/user2/status/0987654321"
    ]
  }'
```

### 3. Root Endpoint

Get service information and available endpoints.

**Endpoint**: `GET /`

**Parameters**: None

**Response**:
```json
{
  "service": "X Post Content Extraction Service",
  "version": "1.0.0",
  "status": "running",
  "endpoints": {
    "health": "/api/health",
    "extract": "/api/extract",
    "docs": "disabled"
  }
}
```

**Status Codes**:
- `200 OK`: Service information retrieved successfully

**Example**:
```bash
curl http://localhost:3000/
```

## Data Models

### ExtractRequest

Request model for post extraction.

```json
{
  "urls": [
    "https://x.com/username/status/1234567890"
  ]
}
```

**Fields**:
- `urls` (array of strings): List of X post URLs to extract content from

**Validation**:
- Must contain at least 1 URL
- Maximum 50 URLs per request
- URLs must be valid X.com or Twitter.com URLs

### PostContent

Extracted post content model.

```json
{
  "post_url": "https://x.com/username/status/1234567890",
  "post_id": "1234567890",
  "author": {
    "username": "username",
    "display_name": "Display Name",
    "profile_image_url": "https://pbs.twimg.com/profile_images/...",
    "verified": false
  },
  "content": "Post content text",
  "timestamp": "2025-07-09T12:00:00.000000",
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
      "preview_url": "https://pbs.twimg.com/media/...",
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
```

### Author

Author information model.

```json
{
  "username": "username",
  "display_name": "Display Name",
  "profile_image_url": "https://pbs.twimg.com/profile_images/...",
  "verified": false
}
```

### Engagement

Engagement metrics model.

```json
{
  "likes": 100,
  "retweets": 50,
  "replies": 25,
  "quotes": 10
}
```

### UrlInfo

URL information model.

```json
{
  "display_url": "t.co/abc123",
  "expanded_url": "https://example.com/full-url",
  "title": "Page Title",
  "description": "Page description"
}
```

### MediaItem

Media item model.

```json
{
  "type": "image",
  "url": "https://pbs.twimg.com/media/...",
  "preview_url": "https://pbs.twimg.com/media/...",
  "alt_text": "Image description",
  "width": 1200,
  "height": 800
}
```

**Media Types**:
- `image`: Static images (JPEG, PNG, GIF)
- `video`: Video files (MP4, etc.)
- `gif`: Animated GIFs

### ReferencedDocument

Referenced document model.

```json
{
  "url": "https://example.com/document.pdf",
  "type": "PDF",
  "title": "Document Title",
  "description": "Document description"
}
```

**Document Types**:
- `PDF`: PDF documents
- `Google Doc`: Google Docs
- `Document`: Other document types

## Rate Limiting

The service implements rate limiting to prevent abuse and ensure fair usage.

### Default Limits

- **Requests**: 100 requests per hour per IP address
- **Window**: 3600 seconds (1 hour)

### Rate Limit Headers

All responses include rate limit information in headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1752068613
```

**Headers**:
- `X-RateLimit-Limit`: Maximum requests allowed in the current window
- `X-RateLimit-Remaining`: Number of requests remaining in the current window
- `X-RateLimit-Reset`: Unix timestamp when the rate limit window resets

### Rate Limit Exceeded

When the rate limit is exceeded, the service returns:

**Status Code**: `429 Too Many Requests`

**Response**:
```json
{
  "error": "Rate limit exceeded",
  "limit": 100,
  "window": 3600,
  "reset_time": 1752068613
}
```

## Error Handling

The service provides structured error responses for all error conditions.

### Error Response Format

```json
{
  "error": "Error message",
  "detail": "Detailed error information",
  "timestamp": "2025-07-09T12:00:00.000000"
}
```

### Common Errors

#### 400 Bad Request

Invalid request format or parameters.

```json
{
  "error": "No URLs provided",
  "detail": null,
  "timestamp": "2025-07-09T12:00:00.000000"
}
```

#### 422 Unprocessable Entity

Request validation failed.

```json
{
  "error": "Validation error",
  "detail": "Invalid request data: [{'field': 'urls', 'message': 'ensure this value has at least 1 items', 'type': 'value_error.list.min_items'}]",
  "timestamp": "2025-07-09T12:00:00.000000"
}
```

#### 429 Too Many Requests

Rate limit exceeded.

```json
{
  "error": "Rate limit exceeded",
  "detail": "100 requests per 3600 seconds",
  "timestamp": "2025-07-09T12:00:00.000000"
}
```

#### 500 Internal Server Error

Server error occurred.

```json
{
  "error": "Internal server error",
  "detail": "An unexpected error occurred. Please try again later.",
  "timestamp": "2025-07-09T12:00:00.000000"
}
```

## Usage Examples

### JavaScript/Node.js

```javascript
const axios = require('axios');

async function extractPosts(urls) {
  try {
    const response = await axios.post('http://localhost:3000/api/extract', {
      urls: urls
    });
    
    console.log(`Successfully extracted ${response.data.posts.length} posts`);
    return response.data;
  } catch (error) {
    if (error.response?.status === 429) {
      console.error('Rate limit exceeded');
    } else {
      console.error('Extraction failed:', error.response?.data || error.message);
    }
    throw error;
  }
}

// Usage
extractPosts(['https://x.com/elonmusk/status/1812258574049157405'])
  .then(result => console.log(result.posts))
  .catch(error => console.error(error));
```

### Python

```python
import httpx
import asyncio

async def extract_posts(urls):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                'http://localhost:3000/api/extract',
                json={'urls': urls}
            )
            response.raise_for_status()
            data = response.json()
            print(f"Successfully extracted {len(data['posts'])} posts")
            return data
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                print("Rate limit exceeded")
            else:
                print(f"Extraction failed: {e.response.text}")
            raise

# Usage
result = asyncio.run(extract_posts([
    'https://x.com/elonmusk/status/1812258574049157405'
]))
print(result['posts'])
```

### PHP

```php
<?php
function extractPosts($urls) {
    $data = json_encode(['urls' => $urls]);
    
    $options = [
        'http' => [
            'header' => "Content-Type: application/json\r\n",
            'method' => 'POST',
            'content' => $data
        ]
    ];
    
    $context = stream_context_create($options);
    $result = file_get_contents('http://localhost:3000/api/extract', false, $context);
    
    if ($result === FALSE) {
        throw new Exception('Request failed');
    }
    
    return json_decode($result, true);
}

// Usage
try {
    $result = extractPosts(['https://x.com/elonmusk/status/1812258574049157405']);
    echo "Successfully extracted " . count($result['posts']) . " posts\n";
    print_r($result['posts']);
} catch (Exception $e) {
    echo "Error: " . $e->getMessage() . "\n";
}
?>
```

## Testing

### Health Check Test

```bash
# Test health endpoint
curl -f http://localhost:3000/api/health || echo "Health check failed"
```

### Extraction Test

```bash
# Test extraction with known working URL
curl -X POST http://localhost:3000/api/extract \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://x.com/elonmusk/status/1812258574049157405"]}' \
  | jq '.success'
```

### Rate Limiting Test

```bash
# Test rate limiting by making multiple requests
for i in {1..5}; do
  echo "Request $i:"
  curl -v http://localhost:3000/api/extract \
    -H "Content-Type: application/json" \
    -d '{"urls": ["https://x.com/test/status/123"]}' \
    2>&1 | grep -E "(X-RateLimit|HTTP/)"
  echo
done
```

## OpenAPI/Swagger Documentation

When running in debug mode (`DEBUG=true`), interactive API documentation is available at:

- **Swagger UI**: `http://localhost:3000/docs`
- **ReDoc**: `http://localhost:3000/redoc`

These interfaces provide interactive API exploration and testing capabilities.

