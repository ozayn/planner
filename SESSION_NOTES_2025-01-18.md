# Session Notes - January 18, 2025
## Instagram API Research & Environment-Aware Development

### Key Learnings

#### 1. Instagram API Reality Check
**Discovery**: Instagram API is not suitable for our use case
- **Instagram Basic Display API**: Only works for your own accounts, deprecated as of Dec 2024
- **Instagram Graph API**: Only works for Instagram Business accounts you own/manage
- **No Public Profile API**: Instagram doesn't provide any official way to access arbitrary public profiles
- **Third-party APIs**: Risky, expensive, violate ToS, frequently shut down

**Conclusion**: Web scraping remains the most practical approach for accessing public Instagram profiles like @baltimore_scenes, @dcphotowalks, etc.

#### 2. Dual Environment Architecture (Critical Learning)
**New Requirement**: All features must work in both local development and Railway deployment

**Environment Differences**:
- **Local Development**: Full resources, longer timeouts, detailed debugging
- **Railway Deployment**: Memory constraints, CPU limits, request timeouts, headless operation

**Implementation Strategy**:
```python
def is_railway_environment():
    return (os.getenv('RAILWAY_ENVIRONMENT') == 'production' or 
            'railway.app' in os.getenv('RAILWAY_PUBLIC_DOMAIN', '') or
            os.getenv('PORT') is not None)

def get_resource_limits():
    if is_railway_environment():
        return {
            'request_timeout': 15,
            'max_retries': 2,
            'delay_between_requests': 2,
            'max_concurrent_requests': 1,
        }
    else:
        return {
            'request_timeout': 30,
            'max_retries': 3,
            'delay_between_requests': 1,
            'max_concurrent_requests': 3,
        }
```

#### 3. Railway Browser Automation Capabilities
**Discovery**: Railway supports both Playwright and Selenium
- **Playwright**: Official Railway template available, better for modern web scraping
- **Selenium**: Railway Grid template available, good for legacy compatibility
- **Resource Considerations**: Both are memory/CPU intensive, need optimization for Railway

**Future Implementation Path**:
- Phase 1: Enhanced web scraping (current)
- Phase 2: Browser automation with Playwright on Railway
- Phase 3: Instagram post content extraction
- Phase 4: AI-powered event detection

#### 4. Instagram Scraping Challenges
**Current Limitations**:
- Instagram heavily protects profile data
- Even major accounts (@natgeo, @instagram, @nasa) return minimal public info
- JavaScript-rendered content makes traditional scraping difficult
- Rate limiting and IP blocking are aggressive

**What We Can Extract**:
- ✅ Profile URL, username/handle, basic existence
- ❌ Follower count, bio, recent posts (requires login/API)

**Enhanced Scraping Improvements**:
- Environment-aware User-Agent selection
- Retry logic with exponential backoff
- Memory management for Railway
- Session management for better reliability

#### 5. Future Instagram Post Extraction Strategy
**Architecture Designed**:
- Environment detection and resource optimization
- Browser automation fallback system
- Background job processing for heavy operations
- AI-powered event detection pipeline
- Graceful degradation between environments

**Key Components**:
- Local: Full browser automation with debugging
- Railway: Headless browsers with memory optimization
- Caching strategy to reduce Instagram requests
- Background job queue for processing

### Technical Implementations

#### Enhanced Source Scraper
- Added environment detection functions
- Implemented adaptive resource limits
- Enhanced retry logic and error handling
- Memory cleanup for Railway deployment
- Dual User-Agent strategy (local vs Railway)

#### Environment-Aware Architecture
- Automatic environment detection
- Resource limit adaptation
- Memory management optimization
- Request timeout optimization
- Concurrent request limiting

### Current Status

#### Completed Features
- ✅ Environment-aware Instagram profile scraping
- ✅ Enhanced web scraping with retry logic
- ✅ Dual environment resource optimization
- ✅ Memory management for Railway
- ✅ Comprehensive strategy documentation

#### Known Issues
- ❌ OAuth logout not working properly on Railway
- ❌ Limited Instagram data extraction (expected)
- ❌ Instagram post content not accessible (future work)

#### Future Development Path
1. **Immediate**: Fix OAuth logout issue
2. **Short-term**: Integrate scraper into admin interface
3. **Medium-term**: Implement browser automation for post extraction
4. **Long-term**: AI-powered event detection from Instagram posts

### Key Files Created/Modified

#### New Files
- `INSTAGRAM_EVENT_EXTRACTION_STRATEGY.md`: Comprehensive strategy for dual-environment Instagram post scraping
- `INSTAGRAM_API_SETUP.md`: Analysis of Instagram API limitations and alternatives

#### Modified Files
- `scripts/source_scraper.py`: Enhanced with environment-aware capabilities
- Added environment detection functions
- Implemented adaptive resource limits
- Enhanced error handling and retry logic

### Lessons Learned

#### 1. Always Plan for Dual Environments
From now on, every feature must be designed to work in both local development and Railway deployment. This affects:
- Resource usage patterns
- Timeout configurations
- Memory management
- Error handling strategies
- User experience design

#### 2. Instagram API is Not the Solution
For accessing public Instagram profiles we don't own, web scraping is the only viable approach. Official APIs are restricted to owned accounts only.

#### 3. Railway Resource Constraints are Real
Railway's free/starter tiers have significant memory and CPU limitations that require:
- Conservative resource usage
- Optimized algorithms
- Background job processing
- Graceful degradation

#### 4. Browser Automation is Possible on Railway
Railway supports Playwright/Selenium but requires careful resource management and optimization.

### Next Session Priorities

#### High Priority
1. Fix OAuth logout functionality
2. Integrate enhanced scraper into admin interface
3. Test Railway deployment with new scraping features

#### Medium Priority
1. Implement browser automation foundation
2. Create background job system for heavy scraping
3. Add caching layer to reduce Instagram requests

#### Low Priority
1. AI-powered event detection research
2. Real-time processing capabilities
3. Advanced Instagram post content extraction

### Development Philosophy Established

**"Dual Environment First"**: Every feature must work seamlessly in both local development and Railway deployment, with appropriate optimizations for each environment's constraints and capabilities.

This approach ensures:
- Consistent development experience
- Production-ready code from day one
- Optimal resource utilization
- Scalable architecture
- Reliable deployment pipeline




