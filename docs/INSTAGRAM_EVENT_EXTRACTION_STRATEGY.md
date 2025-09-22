# Instagram Event Extraction Strategy
## Dual Environment Support (Local + Railway)

### Overview
This document outlines our approach for extracting events from Instagram posts, designed to work in both local development and Railway deployment environments.

## Architecture Approach

### Phase 1: Enhanced Web Scraping (Current)
**Local Environment:**
- Full `requests + BeautifulSoup` capabilities
- No resource constraints
- Real-time scraping during admin operations

**Railway Environment:**
- Same approach but with timeouts and rate limiting
- Cached results to reduce API calls
- Background job processing for heavy operations

### Phase 2: Browser Automation (Future)
**Local Environment:**
- Full Playwright/Selenium with GUI browsers
- Multiple browser instances
- Interactive debugging capabilities
- Full Instagram post content access

**Railway Environment:**
- Headless browser automation using Railway's Playwright template
- Single browser instance to conserve memory
- Optimized for Railway's resource limits
- Background job queue for scraping tasks

## Implementation Strategy

### Current Implementation (Phase 1)
```python
# Environment-aware scraping
def scrape_instagram_posts(username, limit=10):
    if is_railway_environment():
        # Railway: Conservative approach
        return scrape_posts_lightweight(username, limit=5)
    else:
        # Local: Full scraping capabilities
        return scrape_posts_full(username, limit)
```

### Future Implementation (Phase 2)
```python
# Browser automation with environment detection
def scrape_posts_with_browser(username):
    if is_railway_environment():
        # Railway: Headless, memory-optimized
        return scrape_with_playwright_headless(username)
    else:
        # Local: Full browser with debugging
        return scrape_with_playwright_full(username)
```

## Environment Detection

### Environment Variables
```python
import os

def is_railway_environment():
    return os.getenv('RAILWAY_ENVIRONMENT') == 'production'

def is_local_development():
    return os.getenv('FLASK_ENV') == 'development' or not is_railway_environment()

def get_resource_limits():
    if is_railway_environment():
        return {
            'max_browser_instances': 1,
            'request_timeout': 30,
            'max_posts_per_scrape': 5,
            'use_headless': True
        }
    else:
        return {
            'max_browser_instances': 3,
            'request_timeout': 60,
            'max_posts_per_scrape': 20,
            'use_headless': False
        }
```

## Dependency Management

### requirements.txt additions
```
# Web scraping (both environments)
requests>=2.31.0
beautifulsoup4>=4.12.0

# Browser automation (conditional)
playwright>=1.40.0; platform_system != "Railway" or sys_platform == "linux"
selenium>=4.15.0; platform_system != "Railway" or sys_platform == "linux"

# Background jobs
celery>=5.3.0
redis>=5.0.0
```

### Railway-specific setup
```dockerfile
# In railway.json or Dockerfile
RUN playwright install chromium --with-deps
```

## Event Extraction Pipeline

### Stage 1: Post Collection
**Local:**
- Real-time scraping with immediate results
- Full post content and metadata
- Interactive error handling

**Railway:**
- Background job queue
- Batch processing
- Cached results with TTL

### Stage 2: Event Detection
**Both Environments:**
- NLP processing for event keywords
- Date/time extraction
- Location parsing
- Confidence scoring

### Stage 3: Event Creation
**Both Environments:**
- Automatic event creation for high-confidence matches
- Manual review queue for uncertain matches
- Integration with existing venue/city data

## Resource Optimization

### Memory Management
```python
def optimize_for_environment():
    if is_railway_environment():
        # Railway: Conservative memory usage
        gc.collect()
        limit_concurrent_operations(max_concurrent=1)
    else:
        # Local: Use available resources
        limit_concurrent_operations(max_concurrent=5)
```

### Caching Strategy
```python
# Redis cache for Railway, local cache for development
cache_backend = RedisCache() if is_railway_environment() else LocalCache()
```

## Background Jobs Architecture

### Local Development
```python
# Simple threading for immediate feedback
import threading

def scrape_posts_background(source_id):
    thread = threading.Thread(target=scrape_and_process, args=(source_id,))
    thread.start()
```

### Railway Deployment
```python
# Celery with Redis for production
from celery import Celery

app = Celery('instagram_scraper')
app.config_from_object('celeryconfig')

@app.task
def scrape_posts_task(source_id):
    return scrape_and_process(source_id)
```

## Monitoring and Logging

### Environment-Specific Logging
```python
import logging

def setup_logging():
    if is_railway_environment():
        # Railway: Structured logging for cloud monitoring
        logging.basicConfig(
            level=logging.INFO,
            format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
        )
    else:
        # Local: Human-readable logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
```

## Error Handling

### Graceful Degradation
```python
def scrape_with_fallback(username):
    try:
        # Try advanced browser automation
        return scrape_with_playwright(username)
    except (MemoryError, TimeoutError) as e:
        if is_railway_environment():
            # Railway: Fall back to lightweight scraping
            logger.warning(f"Browser automation failed, using lightweight scraping: {e}")
            return scrape_with_requests(username)
        else:
            # Local: Re-raise for debugging
            raise e
```

## Testing Strategy

### Local Testing
- Full integration tests with real Instagram data
- Browser automation testing
- Performance profiling

### Railway Testing
- Resource-constrained testing
- Timeout simulation
- Memory limit testing
- Background job testing

## Deployment Considerations

### Railway Configuration
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python railway_data_loader.py && celery worker --detach && gunicorn app:app --bind 0.0.0.0:$PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  },
  "variables": {
    "RAILWAY_ENVIRONMENT": "production",
    "PLAYWRIGHT_BROWSERS_PATH": "/app/.cache/ms-playwright"
  }
}
```

### Environment Variables
- `RAILWAY_ENVIRONMENT`: Detect deployment environment
- `INSTAGRAM_SCRAPING_ENABLED`: Feature flag
- `MAX_SCRAPING_WORKERS`: Resource allocation
- `SCRAPING_RATE_LIMIT`: Requests per minute

## Future Enhancements

### Phase 3: AI-Powered Event Detection
- Use local LLMs for event classification
- Environment-aware model selection (smaller models for Railway)
- Confidence-based processing

### Phase 4: Real-time Processing
- WebSocket updates for local development
- Server-sent events for Railway deployment
- Progressive enhancement based on environment capabilities

## Implementation Priority

1. **Immediate**: Environment detection and resource optimization
2. **Short-term**: Enhanced web scraping with fallbacks
3. **Medium-term**: Browser automation with Railway template
4. **Long-term**: AI-powered event extraction and real-time processing





