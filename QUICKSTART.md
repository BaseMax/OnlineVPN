# OnlineVPN Quick Start Guide

Get OnlineVPN up and running in 5 minutes!

## Prerequisites

- Docker (20.10+)
- Docker Compose (2.0+)
- Two domain names (optional, can use localhost for testing)

## Installation Steps

### 1. Clone Repository

```bash
git clone https://github.com/BaseMax/OnlineVPN.git
cd OnlineVPN
```

### 2. Configure Domains (Optional)

For production with custom domains:

**Edit nginx/conf.d/vpn-app-1.conf:**
```nginx
server_name your-domain-1.com;  # Replace domain1.example.com
```

**Edit nginx/conf.d/vpn-app-2.conf:**
```nginx
server_name your-domain-2.com;  # Replace domain2.example.com
```

### 3. Start Services

```bash
docker compose up -d
```

Wait 30-60 seconds for services to be healthy.

### 4. Verify Installation

```bash
# Check service status
docker compose ps

# Check health
curl http://localhost:8080/health
curl http://localhost:8081/health
```

Expected output:
```json
{"status": "healthy"}
```

### 5. Access the Application

**Via localhost:**
- Instance 1: http://localhost:8080
- Instance 2: http://localhost:8081

**Via domains (if configured):**
- Domain 1: http://your-domain-1.com
- Domain 2: http://your-domain-2.com

**Via nginx (localhost):**
- http://localhost

## Using the VPN Proxy

### Basic Usage

1. Open http://localhost:8080 in your browser
2. Enter a target URL (e.g., `https://example.com`)
3. Optionally add domains to forward (one per line)
4. Click "Access via Proxy"

### Example with Domain Forwarding

**Target URL:** `https://news.example.com`

**Domains to forward:**
```
cdn.example.com
static.example.com
api.example.com
```

The proxy will fetch the page and route the specified domains through the proxy server.

## Common Commands

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f vpn-app-1
docker compose logs -f nginx
```

### Restart Services
```bash
# All services
docker compose restart

# Specific service
docker compose restart vpn-app-1
```

### Stop Services
```bash
docker compose down
```

### Rebuild and Restart
```bash
docker compose up -d --build
```

## Architecture

```
┌─────────────────────────────────────────────┐
│             Internet/Users                  │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│      Nginx Reverse Proxy (Port 80/443)     │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │ domain1.example.com → vpn-app-1:5000   │ │
│  │ domain2.example.com → vpn-app-2:5000   │ │
│  └────────────────────────────────────────┘ │
└─────────────┬──────────────┬────────────────┘
              │              │
     ┌────────▼─────┐   ┌───▼────────┐
     │  VPN App 1   │   │  VPN App 2 │
     │  Port 8080   │   │  Port 8081 │
     └──────────────┘   └────────────┘
```

## Port Mapping

| Service | Internal | External | Description |
|---------|----------|----------|-------------|
| vpn-app-1 | 5000 | 8080 | First instance |
| vpn-app-2 | 5000 | 8081 | Second instance |
| nginx | 80 | 80 | HTTP traffic |
| nginx | 443 | 443 | HTTPS traffic |

## Troubleshooting

### Services Won't Start

```bash
# Check for port conflicts
netstat -tuln | grep -E '8080|8081|80|443'

# View error logs
docker compose logs

# Force recreate
docker compose down
docker compose up -d --force-recreate
```

### Cannot Access via Domain

1. Verify DNS records:
   ```bash
   nslookup your-domain.com
   dig your-domain.com
   ```

2. Check nginx configuration:
   ```bash
   docker compose exec nginx nginx -t
   ```

3. View nginx logs:
   ```bash
   docker compose logs nginx
   ```

### Health Check Fails

```bash
# Check if services are running
docker compose ps

# Check logs for errors
docker compose logs vpn-app-1
docker compose logs vpn-app-2

# Restart unhealthy service
docker compose restart vpn-app-1
```

## Next Steps

- **Production Setup:** See [DEPLOYMENT.md](DEPLOYMENT.md) for SSL/TLS configuration
- **Advanced Usage:** Check [USAGE_EXAMPLE.md](USAGE_EXAMPLE.md) for examples
- **Security:** Configure HTTPS with Let's Encrypt certificates
- **Monitoring:** Set up health check monitoring
- **Scaling:** Add more instances as needed

## Need Help?

- **Documentation:** [README.md](README.md), [DEPLOYMENT.md](DEPLOYMENT.md)
- **Issues:** https://github.com/BaseMax/OnlineVPN/issues

## Security Notes

⚠️ **Important for Production:**

1. **Always use HTTPS** in production
2. **Configure firewall** to only allow necessary ports
3. **Keep Docker images updated** regularly
4. **Use strong SSL/TLS certificates** from trusted CAs
5. **Monitor logs** for suspicious activity

## License

GPL-3.0 License - See [LICENSE](LICENSE) for details.

---

**That's it!** You now have OnlineVPN running with two instances behind an nginx reverse proxy. 🎉
