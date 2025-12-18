# OnlineVPN

The OnlineVPN is a web-based platform designed in Python that provides you a home page where you can enter any page URL that you want to access, along with a list of domains or subdomains that should be replaced. The system will fetch the content from the server and act as a proxy, replacing all URLs matching the specified domains with mirror proxy links.

## Features

- **URL Proxy/Mirror**: Access any website through the proxy service
- **Domain Replacement**: Automatically replaces specified domains in fetched content
- **Multiple Protocol Support**: Handles both HTTP and HTTPS protocols
- **Subdomain Support**: Replaces both `domain.com` and `www.domain.com` variants
- **Content Type Processing**: Processes HTML, JavaScript, JSON, and XML content
- **Dual Domain Deployment**: Designed to be deployed on two domains:
  - `proxy.maxbase.ir` - Main proxy entry point
  - `mirror.proxy.maxbase.ir` - Mirror domain for replaced URLs

## How It Works

1. User enters a target URL (e.g., `https://youtube.com/watch`)
2. User specifies domains to replace (e.g., `youtube.com`, `www.youtube.com`)
3. The system fetches the content from the target URL
4. All occurrences of the specified domains (with http/https) are replaced with `https://mirror.proxy.maxbase.ir/$resturl`
5. The processed content is returned to the user

### Example

**Input:**
- Target URL: `https://youtube.com/watch`
- Domains: `youtube.com`, `www.youtube.com`

**Result:**
- `https://youtube.com/video` → `https://mirror.proxy.maxbase.ir/video`
- `http://youtube.com/api` → `https://mirror.proxy.maxbase.ir/api`
- `https://www.youtube.com/embed` → `https://mirror.proxy.maxbase.ir/embed`
- `http://www.youtube.com/thumbnail` → `https://mirror.proxy.maxbase.ir/thumbnail`

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/BaseMax/OnlineVPN.git
cd OnlineVPN
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the domains (optional):
Edit `config.py` to change the proxy and mirror domain settings:
```python
PROXY_DOMAIN = "proxy.maxbase.ir"
MIRROR_DOMAIN = "mirror.proxy.maxbase.ir"
```

## Usage

### Development

Run the Flask development server:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

### Production Deployment

For production deployment, use a WSGI server like Gunicorn:

1. Install Gunicorn:
```bash
pip install gunicorn
```

2. Run with Gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Or use uWSGI:
```bash
uwsgi --http 0.0.0.0:5000 --module app:app --processes 4
```

### Docker Deployment (Optional)

Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

Build and run:
```bash
docker build -t onlinevpn .
docker run -p 5000:5000 onlinevpn
```

## Testing

Run the URL replacement tests:
```bash
python test_url_replacement.py
```

## Configuration

The `config.py` file contains the following settings:

- `PROXY_DOMAIN`: The main proxy domain
- `MIRROR_DOMAIN`: The mirror domain for replaced URLs
- `REQUEST_TIMEOUT`: Timeout for fetching remote content (default: 30 seconds)
- `USER_AGENT`: User agent string for requests
- `PROCESSABLE_CONTENT_TYPES`: List of content types that should be processed for URL replacement

## API Endpoints

### GET `/`
Returns the home page with the proxy form.

### POST `/proxy`
Processes a proxy request.

**Form Parameters:**
- `url` (required): The target URL to proxy
- `domains` (required): Newline-separated list of domains to replace

**Example:**
```bash
curl -X POST http://localhost:5000/proxy \
  -d "url=https://youtube.com/watch" \
  -d "domains=youtube.com
www.youtube.com"
```

## Security Considerations

- This is a proxy service that fetches external content. Use with caution in production.
- Consider implementing rate limiting to prevent abuse
- Add authentication for production use
- Be aware of legal implications of proxying content
- Consider implementing content filtering and sanitization

## License

This project is licensed under the GPL-3.0 License - see the LICENSE file for details.

## Author

**Max Base**

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
