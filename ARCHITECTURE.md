# OnlineVPN Architecture

## Overview

OnlineVPN is a web-based proxy service with a clean, single-domain architecture that supports both traditional websites and modern Single Page Applications (SPAs/PWAs).

## Design Principles

1. **Simplicity**: Single domain, GET-based routing with query parameters
2. **Smart Proxying**: Only proxy specified domains, leave others unchanged
3. **Session Persistence**: Remember domains across navigation
4. **SPA Support**: Proper handling of client-side routing
5. **Security**: SSRF protection, input validation

## URL Structure

### Home Page
```
https://proxy.maxbase.ir/
```

### Proxy Request
```
https://proxy.maxbase.ir/proxy?url=<target_url>&domains=<domain1,domain2>
```

**Parameters:**
- `url` (required): The target URL to proxy
- `domains` (optional): Comma-separated list of domains to proxy

**Examples:**
```
# Single domain
https://proxy.maxbase.ir/proxy?url=https://example.com&domains=example.com

# Multiple domains
https://proxy.maxbase.ir/proxy?url=https://github.com&domains=github.com,github.githubassets.com

# Auto-detect (uses target domain)
https://proxy.maxbase.ir/proxy?url=https://example.com
```

## How URL Replacement Works

### 1. Allowed Domains Only

Only URLs matching the specified domains are replaced with proxy URLs. This means:
- ✅ `https://example.com/page` → Proxied (if in allowed list)
- ❌ `https://google.com/search` → Not proxied (external link)
- ✅ `https://cdn.example.com/file.js` → Proxied (if in allowed list)

### 2. Session-Based Tracking

When you access a proxied page:
1. Allowed domains are stored in your session
2. Links within proxied pages automatically maintain the domain list
3. You can navigate naturally without re-entering domains

### 3. URL Types Handled

**Absolute URLs:**
```html
<a href="https://example.com/page">Link</a>
→ <a href="https://proxy.maxbase.ir/proxy?url=https%3A//example.com/page&domains=...">Link</a>
```

**Relative URLs:**
```html
<a href="/about">About</a>
→ <a href="https://proxy.maxbase.ir/proxy?url=https%3A//example.com/about&domains=...">About</a>
```

**Protocol-relative URLs:**
```html
<script src="//cdn.example.com/app.js"></script>
→ <script src="https://proxy.maxbase.ir/proxy?url=https%3A//cdn.example.com/app.js&domains=..."></script>
```

## SPA/PWA Support

### Challenge

Single Page Applications (React, Vue, Angular) use client-side routing:
- URLs like `/about` don't make server requests
- JavaScript updates the URL via History API
- Server must serve the app for all routes

### Solution

1. **Session Persistence**: Domains stored in session remain across navigation
2. **GET Parameters**: All proxy info in URL, works with client-side routing
3. **Content Processing**: JavaScript files get URL replacements for API calls
4. **No Route Conflicts**: `/proxy` route doesn't conflict with app routes

### Example: React App

```
1. User visits: https://proxy.maxbase.ir/proxy?url=https://app.example.com&domains=app.example.com,api.example.com

2. Server fetches and processes the React app HTML

3. User clicks internal link: /dashboard
   - React handles routing client-side
   - App makes API call to /api/data
   - API URL replaced: https://proxy.maxbase.ir/proxy?url=https://api.example.com/data&...

4. Everything works seamlessly!
```

## Request Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User Request                                             │
│    GET /proxy?url=https://example.com&domains=example.com   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Validation                                               │
│    - URL format check                                       │
│    - SSRF protection (no internal IPs)                      │
│    - Session management                                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Fetch Content                                            │
│    - Request to target URL                                  │
│    - Stream response                                        │
│    - Preserve headers                                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Process Content (if text)                                │
│    - Replace URLs for allowed domains                       │
│    - Leave external links unchanged                         │
│    - Handle relative URLs                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Return to User                                           │
│    - Modified HTML/JS/CSS                                   │
│    - Or streamed binary content                             │
└─────────────────────────────────────────────────────────────┘
```

## Security Features

### SSRF Protection

Prevents access to internal networks:
- `10.0.0.0/8` (Private network)
- `172.16.0.0/12` (Private network)
- `192.168.0.0/16` (Private network)
- `127.0.0.0/8` (Loopback)
- IPv6 private ranges

### Input Validation

- URL format validation
- Protocol whitelist (HTTP/HTTPS only)
- Domain validation

### Session Security

- Flask session with secret key
- HTTPOnly cookies
- Secure cookie flag (in production)

## Performance Optimization

### Streaming

Binary content (images, videos, files) is streamed efficiently:
```python
def stream_response_content(response_obj):
    for chunk in response_obj.iter_content(chunk_size=8192):
        yield chunk
```

Benefits:
- No memory overhead for large files
- Fast response times
- Scalable to large files

### Content Type Detection

Only text-based content is processed for URL replacement:
```python
PROCESSABLE_CONTENT_TYPES = [
    'text/',
    'application/javascript',
    'application/json',
    'application/xml'
]
```

Binary content is streamed directly without processing.

## Deployment

### Single Instance
```bash
python app.py
```

### Docker
```bash
docker-compose up -d
```

### Production Considerations

1. **Secret Key**: Change `app.secret_key` in production
2. **SSL/TLS**: Use HTTPS in production
3. **WSGI Server**: Use Gunicorn or uWSGI
4. **Reverse Proxy**: Nginx or similar
5. **Session Storage**: Consider Redis for distributed sessions

## Comparison: Old vs New

| Feature | Old Architecture | New Architecture |
|---------|-----------------|------------------|
| **Domains** | 2 (proxy + mirror) | 1 (proxy only) |
| **Routing** | POST /proxy | GET /proxy |
| **URL Format** | /p/encoded/path | ?url=...&domains=... |
| **Link Replacement** | All links | Specified domains only |
| **Session** | None | Domain tracking |
| **SPA Support** | Limited | Full support |
| **Complexity** | High | Low |
| **Maintainability** | Difficult | Easy |

## Future Enhancements

Possible improvements:
- [ ] User accounts for saved domain lists
- [ ] History tracking
- [ ] Cookie handling improvements
- [ ] WebSocket proxy support
- [ ] Browser extension
- [ ] Rate limiting
- [ ] Caching layer

## Troubleshooting

### Links not working?
- Ensure domain is in allowed list
- Check browser console for errors
- Verify session is active

### SPA routing issues?
- Ensure all API domains are in allowed list
- Check JavaScript console for CORS errors
- Verify content type detection

### Performance issues?
- Check network latency to target site
- Consider caching layer
- Monitor memory usage
- Use production WSGI server

## Contributing

When contributing:
1. Keep code simple and clean
2. Add tests for new features
3. Update documentation
4. Follow existing code style
5. Test with both traditional and SPA sites
