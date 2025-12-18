# Online VPN

> A clean, simple, and powerful web-based proxy platform designed in Python (Flask). Browse any website through the proxy with seamless navigation and support for both traditional and Single Page Applications (SPAs/PWAs).

A modern Python-based web proxy service for secure, flexible, and privacy-focused browsing. This project uses Flask and Requests to proxy web traffic, rewrite URLs, and provide SSRF protection, CORS support, and easy deployment via Docker and Nginx.

![Online VPN](preview.jpg)

## Features

- **Unified Proxy Domain:** All proxied traffic routes through a single domain (default: `proxy.maxbase.ir`).
- **Flexible URL Rewriting:** Automatically rewrites absolute and protocol-relative URLs for seamless proxying.
- **SSRF Protection:** Blocks requests to private and unsafe IP ranges.
- **CORS Support:** Configurable CORS headers for cross-origin requests.
- **Customizable Timeout & SSL:** Set request timeouts and toggle SSL verification for upstream requests.
- **Docker & Nginx Ready:** Includes Dockerfile and Nginx configs for scalable deployment.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the app:**
   ```bash
   python app.py
   ```

3. **Access the setup page:**
   Open [http://localhost:5000/maxme](http://localhost:5000/maxme) in your browser.

4. **Configure target site:**
   - Enter the target URL you want to proxy.
   - Optionally specify domains for URL rewriting.

5. **Browse via proxy:**
   After setup, all requests to `/` or `/<path>` will be proxied through your chosen target.

## Configuration

Edit `config.py` to customize:
- `PROXY_DOMAIN`: Main proxy domain
- `PROXY_ROUTE_PREFIX`: Prefix for proxied routes
- `REQUEST_TIMEOUT`: Upstream request timeout
- `SSL_VERIFY`: SSL certificate verification (can be set via `SSL_VERIFY` env var)
- CORS settings: Allowed origins, methods, headers
- `PROCESSABLE_CONTENT_TYPES`: Content types for URL rewriting

## Deployment

### Docker

1. Build the image:
   ```bash
   docker build -t onlinevpn .
   ```
2. Run with Docker Compose:
   ```bash
   docker-compose up
   ```

### Nginx

- See `nginx/nginx.conf` and `nginx/conf.d/` for sample configs.
- Use Nginx as a reverse proxy for HTTPS and load balancing.

## Security

- SSRF protection blocks requests to private IP ranges.
- SSL verification is configurable (default: disabled for flexibility).
- CORS headers are set for cross-origin support.

## Health Check

- Endpoint: `/health` returns `{"status": "ok"}` for monitoring.

## File Structure

- `app.py`: Main Flask proxy app
- `config.py`: Configuration settings
- `templates/index.html`: Setup page
- `nginx/`: Nginx configs
- `docker-compose.yml`, `Dockerfile`: Containerization
- `test_*.py`: Test scripts

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the GPL-3.0 License. See the [LICENSE](LICENSE) file for details.

Copyright 2025, Seyyed Ali Mohammadiyeh (Max Base)
