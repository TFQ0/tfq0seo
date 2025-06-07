# API Reference

This document provides detailed information about the TFQ0SEO API endpoints, request/response formats, and examples.

## API Versioning

The API uses semantic versioning. The current version is `v1`. Include the version in the URL:
```
https://api.tfq0seo.com/v1/
```

## Authentication

All API requests require authentication. Use your API key in the Authorization header:
```bash
Authorization: Bearer your-api-key
```

## Common Headers

```http
Content-Type: application/json
Accept: application/json
User-Agent: YourApp/1.0
```

## Rate Limiting

- Default: 100 requests per minute
- Enterprise: 1000 requests per minute
- Headers:
  - `X-RateLimit-Limit`: Total requests allowed
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Time until limit resets

## Endpoints

### Analysis

#### Single URL Analysis

```http
POST /v1/analyze
```

Analyzes a single URL for SEO factors.

**Request Body:**
```json
{
    "url": "https://example.com",
    "options": {
        "depth": 1,
        "check_mobile": true,
        "check_performance": true,
        "check_security": true
    }
}
```

**Response:**
```json
{
    "url": "https://example.com",
    "timestamp": "2024-02-20T12:00:00Z",
    "status": "success",
    "analysis": {
        "mobile_friendly": {
            "has_viewport": true,
            "responsive_images": true,
            "touch_friendly": true
        },
        "performance": {
            "resource_count": {
                "images": 10,
                "scripts": 5,
                "styles": 3
            },
            "load_time": 1.5
        },
        "security": {
            "https": true,
            "hsts": true,
            "content_security": true
        },
        "structured_data": {
            "types": ["WebPage", "Organization"],
            "count": 2
        }
    }
}
```

#### Batch Analysis

```http
POST /v1/analyze/batch
```

Analyzes multiple URLs in a single request.

**Request Body:**
```json
{
    "urls": [
        "https://example1.com",
        "https://example2.com"
    ],
    "options": {
        "depth": 1,
        "parallel": true,
        "max_concurrent": 5
    }
}
```

**Response:**
```json
{
    "batch_id": "batch_123xyz",
    "timestamp": "2024-02-20T12:00:00Z",
    "status": "processing",
    "total_urls": 2,
    "completed_urls": 0,
    "results_url": "/v1/analyze/batch/batch_123xyz"
}
```

#### Get Batch Results

```http
GET /v1/analyze/batch/{batch_id}
```

Retrieves results of a batch analysis.

**Response:**
```json
{
    "batch_id": "batch_123xyz",
    "status": "completed",
    "results": {
        "https://example1.com": {
            "status": "success",
            "analysis": { ... }
        },
        "https://example2.com": {
            "status": "success",
            "analysis": { ... }
        }
    }
}
```

### Reports

#### Generate Report

```http
POST /v1/reports
```

Generates a detailed SEO report.

**Request Body:**
```json
{
    "analysis_id": "analysis_123xyz",
    "format": "pdf",
    "sections": ["overview", "mobile", "performance", "security"],
    "include_recommendations": true
}
```

**Response:**
```json
{
    "report_id": "report_123xyz",
    "status": "generating",
    "download_url": "/v1/reports/report_123xyz/download"
}
```

#### Download Report

```http
GET /v1/reports/{report_id}/download
```

Downloads a generated report.

### Monitoring

#### Create Monitor

```http
POST /v1/monitors
```

Creates a monitoring job for continuous analysis.

**Request Body:**
```json
{
    "url": "https://example.com",
    "frequency": "daily",
    "alerts": {
        "email": "alerts@example.com",
        "webhook": "https://example.com/webhook"
    },
    "thresholds": {
        "performance_score": 80,
        "security_score": 90
    }
}
```

**Response:**
```json
{
    "monitor_id": "monitor_123xyz",
    "status": "active",
    "next_run": "2024-02-21T12:00:00Z"
}
```

## Error Handling

### Error Response Format

```json
{
    "error": {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Rate limit exceeded. Please try again in 60 seconds.",
        "details": {
            "limit": 100,
            "reset_at": "2024-02-20T12:01:00Z"
        }
    }
}
```

### Common Error Codes

- `INVALID_REQUEST`: Malformed request or invalid parameters
- `AUTHENTICATION_ERROR`: Invalid or missing API key
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `RESOURCE_NOT_FOUND`: Requested resource doesn't exist
- `ANALYSIS_FAILED`: Analysis operation failed
- `INTERNAL_ERROR`: Server-side error

## Pagination

For endpoints returning lists, use these query parameters:

```
?page=1&per_page=20
```

Response includes pagination metadata:

```json
{
    "data": [...],
    "pagination": {
        "total": 100,
        "per_page": 20,
        "current_page": 1,
        "total_pages": 5,
        "next_page": "/v1/resource?page=2",
        "prev_page": null
    }
}
```

## Code Examples

### Python

```python
import requests

API_KEY = "your-api-key"
BASE_URL = "https://api.tfq0seo.com/v1"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Single URL analysis
response = requests.post(
    f"{BASE_URL}/analyze",
    headers=headers,
    json={
        "url": "https://example.com",
        "options": {"depth": 1}
    }
)

print(response.json())
```

### JavaScript

```javascript
const API_KEY = 'your-api-key';
const BASE_URL = 'https://api.tfq0seo.com/v1';

// Single URL analysis
async function analyzeSite(url) {
    const response = await fetch(`${BASE_URL}/analyze`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${API_KEY}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            url,
            options: { depth: 1 }
        })
    });
    
    return await response.json();
}
```

## Best Practices

1. **Rate Limiting**
   - Implement exponential backoff
   - Cache responses when possible
   - Use batch endpoints for multiple URLs

2. **Error Handling**
   - Always check response status codes
   - Implement retry logic for 5xx errors
   - Log error responses for debugging

3. **Performance**
   - Use connection pooling
   - Enable HTTP keep-alive
   - Compress requests/responses

4. **Security**
   - Never expose API keys in client-side code
   - Use HTTPS for all requests
   - Validate response data

## Support

For API support:
- Email: api-support@tfq0seo.com
- Documentation: https://docs.tfq0seo.com
- Status Page: https://status.tfq0seo.com 