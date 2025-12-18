# Online VPN

The OnlineVPN is a web-based platform designed in Python that provides you a home page where you can enter any page URL that you want to check/watch, and you can enter a list of domains or subdomains that you want to change and forward. The server will send a request to your page and act like a proxy.

## Features

- 🔒 Web-based proxy service
- 🌐 Domain forwarding and replacement
- 🚀 Easy deployment with Docker
- ⚖️ Load balancing with Nginx
- 📦 Multi-instance support

## Quick Start with Docker

### Prerequisites

- Docker Engine (version 20.10+)
- Docker Compose (version 2.0+)
- Two domain names pointing to your server

### Deployment

1. **Clone the repository**
   ```bash
   git clone https://github.com/BaseMax/OnlineVPN.git
   cd OnlineVPN
   ```

2. **Configure your domains**
   
   Edit `nginx/conf.d/vpn-app-1.conf` and `nginx/conf.d/vpn-app-2.conf` to replace `domain1.example.com` and `domain2.example.com` with your actual domains.

3. **Start the services**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Instance 1: `http://localhost:8080`
   - Instance 2: `http://localhost:8081`
   - Via Domain 1: `http://your-domain1.com`
   - Via Domain 2: `http://your-domain2.com`

## Architecture

The deployment consists of:

- **2 Application Instances**: Running on ports 8080 and 8081
- **Nginx Reverse Proxy**: Forwarding 2 domains to the respective application instances on port 80 (HTTP) and 443 (HTTPS)
- **Docker Network**: All services communicate through a bridge network

```
Internet
   ↓
Nginx (Port 80/443)
   ├─→ domain1.example.com → vpn-app-1 (Port 8080)
   └─→ domain2.example.com → vpn-app-2 (Port 8081)
```

## Usage

1. Open the application in your browser
2. Enter the target URL you want to access through the proxy
3. Optionally, enter domains to forward (one per line)
4. Click "Access via Proxy" to fetch the content

## Configuration

### SSL Certificate Verification

By default, SSL certificate verification is **disabled** to allow proxying sites with SSL issues or self-signed certificates. This is necessary for some sites but may expose you to security risks.

To enable SSL certificate verification, set the `SSL_VERIFY` environment variable:

```bash
# Enable SSL verification
export SSL_VERIFY=true
python app.py
```

Or with Docker:

```bash
docker run -e SSL_VERIFY=true ...
```

**Note:** When SSL verification is disabled, a warning message will be displayed in the logs.

## Documentation

For detailed deployment instructions, configuration options, and troubleshooting, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Docker Services

- `vpn-app-1`: First application instance (port 8080)
- `vpn-app-2`: Second application instance (port 8081)
- `nginx`: Reverse proxy for domain forwarding (ports 80, 443)

## Development

To run the application locally without Docker:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

The application will be available at `http://localhost:5000`.

## License

This project is licensed under the GPL-3.0 License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
