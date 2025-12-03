# Image Proxy Technique for Hotlinking Protection

## Problem

Many websites (especially museums and cultural institutions) block hotlinking of images through:
- **Cloudflare Error 1011**: "The owner of this website does not allow hotlinking to that resource"
- **SSL Certificate Verification Errors**: Some sites have certificate issues when accessed programmatically
- **Bot Detection**: Websites may block requests that don't look like legitimate browser requests

When trying to display external images directly in your application, you'll see errors like:
```
Error 1011: The owner of this website (hirshhorn.si.edu) does not allow hotlinking to that resource
```

## Solution

Create an **image proxy endpoint** that:
1. Fetches images server-side with proper headers
2. Bypasses hotlinking protection by mimicking browser requests
3. Serves images through your own server
4. Handles SSL/certificate issues gracefully

## Implementation

### 1. Image Proxy Endpoint (`/api/image-proxy`)

**Location**: `app.py`

```python
@app.route('/api/image-proxy')
def proxy_external_image():
    """Proxy external images to bypass hotlinking restrictions (e.g., Cloudflare)"""
    from flask import request
    from urllib.parse import unquote, quote
    import requests
    from flask import Response
    
    try:
        image_url = request.args.get('url')
        if not image_url:
            return jsonify({'error': 'Missing url parameter'}), 400
        
        # Decode the URL if it was encoded
        image_url = unquote(image_url)
        
        # Validate that it's an HTTP(S) URL
        if not image_url.startswith(('http://', 'https://')):
            return jsonify({'error': 'Invalid URL'}), 400
        
        # Disable SSL verification warnings
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Set proper headers to avoid bot detection and hotlinking restrictions
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://hirshhorn.si.edu/',  # Add referer to make request look legitimate (bypasses hotlinking)
            'Origin': 'https://hirshhorn.si.edu',
        }
        
        # Try regular requests first (works well with proper headers)
        try:
            response = requests.get(image_url, headers=headers, timeout=15, allow_redirects=True, verify=False)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            # If regular requests fails, try cloudscraper (for Cloudflare protection)
            try:
                import cloudscraper
                scraper = cloudscraper.create_scraper()
                app_logger.info(f"Regular request failed, trying cloudscraper for {image_url}")
                response = scraper.get(image_url, headers=headers, timeout=15, allow_redirects=True)
                response.raise_for_status()
            except ImportError:
                # cloudscraper not available, re-raise original error
                raise e
            except Exception as e2:
                # cloudscraper also failed, log and raise
                app_logger.error(f"Both regular requests and cloudscraper failed for {image_url}: {e}, {e2}")
                raise e
        
        # Determine content type
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        if not content_type.startswith('image/'):
            content_type = 'image/jpeg'
        
        # Return the image with proper headers
        return Response(
            response.content,
            mimetype=content_type,
            headers={
                'Cache-Control': 'public, max-age=86400',  # Cache for 24 hours
                'Content-Type': content_type,
                'Access-Control-Allow-Origin': '*'  # Allow cross-origin requests
            }
        )
        
    except requests.exceptions.RequestException as e:
        app_logger.error(f"Error proxying image from {image_url}: {e}")
        return jsonify({'error': f'Failed to fetch image: {str(e)}'}), 500
    except Exception as e:
        app_logger.error(f"Unexpected error proxying image: {e}")
        return jsonify({'error': 'Failed to proxy image'}), 500
```

### 2. Automatic URL Routing in Data Models

Route external image URLs through the proxy automatically in your model's `to_dict()` method:

```python
def to_dict(self):
    """Convert event to dictionary with all relevant fields"""
    from urllib.parse import quote
    
    image_url = self.image_url
    
    # ... existing image URL handling ...
    
    # Route external image URLs through proxy to bypass hotlinking restrictions
    if image_url and isinstance(image_url, str) and image_url.startswith('http'):
        # Check if it's from a domain that blocks hotlinking
        blocked_domains = ['hirshhorn.si.edu', 'si.edu', 'smithsonian.edu']
        if any(domain in image_url for domain in blocked_domains):
            # Route through our proxy endpoint
            encoded_url = quote(image_url, safe='')
            image_url = f"/api/image-proxy?url={encoded_url}"
    
    return {
        # ... other fields ...
        'image_url': image_url,
        # ...
    }
```

### 3. Usage in Frontend

The frontend doesn't need any changes - it just uses the `image_url` from the API:

```html
<img src="{{ event.image_url }}" alt="Event Image">
```

The URL will automatically be routed through the proxy if needed.

## Key Features

### 1. **Hotlinking Protection Bypass**
- Adds `Referer` and `Origin` headers to make requests look legitimate
- Mimics browser behavior to avoid bot detection

### 2. **SSL Certificate Handling**
- Disables SSL verification (`verify=False`) to handle certificate issues
- Suppresses SSL warnings in logs

### 3. **Cloudflare Protection**
- First tries regular `requests` with proper headers
- Falls back to `cloudscraper` if Cloudflare protection is detected
- `cloudscraper` automatically handles Cloudflare challenges

### 4. **Caching**
- Caches images for 24 hours (`max-age=86400`)
- Reduces load on source servers
- Improves response times for repeated requests

### 5. **Error Handling**
- Graceful fallback from regular requests to cloudscraper
- Comprehensive error logging
- Returns proper HTTP error codes

## When to Use This Technique

Use the image proxy when:

1. **Hotlinking Protection**: Website blocks direct image embedding
   - Error 1011 or similar hotlinking errors
   - Images fail to load with CORS or 403 errors

2. **SSL Certificate Issues**: Certificate verification fails
   - SSL: CERTIFICATE_VERIFY_FAILED errors
   - Sites with self-signed or expired certificates

3. **Cloudflare Protection**: Site uses Cloudflare bot protection
   - 403 Forbidden errors
   - Challenge pages or CAPTCHAs

4. **Bot Detection**: Site blocks automated requests
   - Requests fail without proper headers
   - Need to mimic browser behavior

## Configuration

### Adding New Blocked Domains

To automatically route images from new domains through the proxy, add them to the `blocked_domains` list:

```python
blocked_domains = [
    'hirshhorn.si.edu',
    'si.edu',
    'smithsonian.edu',
    'your-domain.com'  # Add new domains here
]
```

### Customizing Headers

Adjust headers based on the target website:

```python
headers = {
    'User-Agent': 'Mozilla/5.0 ...',  # Match browser
    'Referer': 'https://source-website.com/',  # Match source domain
    'Origin': 'https://source-website.com',
    # Add other headers as needed
}
```

### Cache Duration

Adjust cache duration in the response headers:

```python
'Cache-Control': 'public, max-age=86400'  # 24 hours
# Or:
'Cache-Control': 'public, max-age=3600'   # 1 hour
'Cache-Control': 'public, max-age=604800' # 7 days
```

## Testing

### Test the Proxy Endpoint

```bash
# Test with a blocked image URL
curl -I "http://localhost:5001/api/image-proxy?url=https://hirshhorn.si.edu/wp-content/uploads/2012/06/Kruger-Install-Escalator-from-lobby.jpg"

# Should return:
# HTTP/1.1 200 OK
# Content-Type: image/jpeg
# Cache-Control: public, max-age=86400
```

### Test in Python

```python
from app import app, db, Event
with app.app_context():
    event = Event.query.first()
    event_dict = event.to_dict()
    print(f"Image URL: {event_dict['image_url']}")
    # Should show proxied URL if from blocked domain
```

## Dependencies

Make sure these are in your `requirements.txt`:

```
requests
cloudscraper  # For Cloudflare protection bypass
urllib3       # Usually included with requests
```

## Security Considerations

1. **Input Validation**: Always validate and sanitize the URL parameter
   - Only allow HTTP/HTTPS URLs
   - Consider whitelisting allowed domains

2. **Rate Limiting**: Implement rate limiting to prevent abuse
   - Limit requests per IP
   - Limit image size

3. **Size Limits**: Set maximum image size to prevent DoS
   ```python
   MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
   if len(response.content) > MAX_IMAGE_SIZE:
       return jsonify({'error': 'Image too large'}), 400
   ```

4. **Domain Whitelisting**: Only allow specific domains
   ```python
   ALLOWED_DOMAINS = ['hirshhorn.si.edu', 'si.edu']
   parsed_url = urlparse(image_url)
   if parsed_url.netloc not in ALLOWED_DOMAINS:
       return jsonify({'error': 'Domain not allowed'}), 403
   ```

## Example: Using in Other Contexts

### For Venue Images

```python
class Venue(db.Model):
    def to_dict(self):
        image_url = self.image_url
        if image_url and image_url.startswith('http'):
            if any(blocked in image_url for blocked in ['si.edu', 'smithsonian.edu']):
                from urllib.parse import quote
                image_url = f"/api/image-proxy?url={quote(image_url, safe='')}"
        return {'image_url': image_url, ...}
```

### For Source Images

```python
class Source(db.Model):
    def to_dict(self):
        image_url = self.image_url
        if image_url and needs_proxy(image_url):
            image_url = proxy_url(image_url)
        return {'image_url': image_url, ...}

def needs_proxy(url):
    blocked_domains = ['hirshhorn.si.edu', 'si.edu']
    return any(domain in url for domain in blocked_domains)

def proxy_url(url):
    from urllib.parse import quote
    return f"/api/image-proxy?url={quote(url, safe='')}"
```

## Troubleshooting

### Images Still Not Loading

1. **Check Logs**: Look for errors in `logs/app.log`
   ```
   tail -f logs/app.log | grep -i "proxy\|image"
   ```

2. **Test Direct URL**: Verify the source URL works
   ```bash
   curl -I "https://hirshhorn.si.edu/wp-content/uploads/..."
   ```

3. **Test Proxy**: Test the proxy endpoint directly
   ```bash
   curl "http://localhost:5001/api/image-proxy?url=..."
   ```

4. **Check Headers**: Verify headers are correct for the target site

### SSL Errors

If you still get SSL errors:
- Ensure `verify=False` is set
- Check if certificates need to be updated
- Consider using cloudscraper exclusively

### Cloudflare Blocking

If Cloudflare still blocks requests:
- Ensure `cloudscraper` is installed
- Check that headers match the source site
- Verify the Referer header matches the source domain

## Related Files

- `app.py`: Main proxy endpoint implementation
- `scripts/venue_event_scraper.py`: Where images are initially scraped
- `templates/admin.html`: Where images are displayed
- `requirements.txt`: Dependencies

## References

- [Cloudflare Error 1011 Documentation](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-1xxx-errors/error-1011/)
- [Cloudscraper Documentation](https://github.com/VeNoMouS/cloudscraper)
- [Requests Library SSL Verification](https://requests.readthedocs.io/en/latest/user/advanced/#ssl-cert-verification)

