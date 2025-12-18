# OnlineVPN Deployment Guide

This guide explains how to deploy the OnlineVPN application using Docker and docker-compose with nginx reverse proxy.

## Architecture Overview

The deployment consists of:
- **2 Application Instances**: Running on ports 8080 and 8081
- **Nginx Reverse Proxy**: Forwarding 2 domains to the respective application instances
- **Docker Network**: All services communicate through a bridge network

## Prerequisites

- Docker Engine (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)
- Two domain names (or subdomains) pointing to your server

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/BaseMax/OnlineVPN.git
cd OnlineVPN
```

### 2. Configure Domain Names

Edit the nginx configuration files to use your actual domain names:

**For Domain 1** - Edit `nginx/conf.d/vpn-app-1.conf`:
```nginx
server_name your-domain1.com;  # Replace domain1.example.com
```

**For Domain 2** - Edit `nginx/conf.d/vpn-app-2.conf`:
```nginx
server_name your-domain2.com;  # Replace domain2.example.com
```

### 3. Build and Start Services

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 4. Verify Deployment

- Application Instance 1: `http://localhost:8080`
- Application Instance 2: `http://localhost:8081`
- Via Domain 1: `http://your-domain1.com`
- Via Domain 2: `http://your-domain2.com`

## Port Configuration

The deployment uses the following ports:

| Service | Internal Port | External Port | Description |
|---------|--------------|---------------|-------------|
| vpn-app-1 | 5000 | 8080 | First application instance |
| vpn-app-2 | 5000 | 8081 | Second application instance |
| nginx | 80 | 80 | HTTP traffic |
| nginx | 443 | 443 | HTTPS traffic (optional) |

## Nginx Configuration

### HTTP Setup (Default)

The default configuration serves traffic over HTTP on port 80. Each domain is forwarded to its respective application instance:

- `domain1.example.com` → `vpn-app-1:5000` (port 8080)
- `domain2.example.com` → `vpn-app-2:5000` (port 8081)

### HTTPS Setup (Optional)

To enable HTTPS:

1. **Obtain SSL Certificates**
   ```bash
   # Using Let's Encrypt (recommended)
   certbot certonly --standalone -d your-domain1.com -d your-domain2.com
   ```

2. **Update docker-compose.yml**
   
   Add SSL certificate volumes to the nginx service:
   ```yaml
   nginx:
     volumes:
       - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
       - ./nginx/conf.d:/etc/nginx/conf.d:ro
       - /etc/letsencrypt:/etc/letsencrypt:ro  # Add this line
   ```

3. **Uncomment HTTPS Configuration**
   
   In `nginx/conf.d/vpn-app-1.conf` and `vpn-app-2.conf`, uncomment the HTTPS server block and update certificate paths:
   ```nginx
   server {
       listen 443 ssl http2;
       server_name your-domain1.com;
       
       ssl_certificate /etc/letsencrypt/live/your-domain1.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/your-domain1.com/privkey.pem;
       # ... rest of configuration
   }
   ```

4. **Restart Services**
   ```bash
   docker-compose restart nginx
   ```

## Docker Commands

### Managing Services

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart a specific service
docker-compose restart vpn-app-1

# View logs
docker-compose logs -f vpn-app-1
docker-compose logs -f nginx

# Rebuild and restart
docker-compose up -d --build
```

### Scaling

To add more application instances:

1. Edit `docker-compose.yml`:
   ```yaml
   vpn-app-3:
     build: .
     container_name: onlinevpn-app-3
     ports:
       - "8082:5000"
     # ... rest of configuration
   ```

2. Add nginx configuration for the third domain
3. Restart services

### Monitoring

```bash
# Check service health
docker-compose ps

# View resource usage
docker stats

# Access container shell
docker exec -it onlinevpn-app-1 /bin/bash
```

## Environment Variables

You can customize the application behavior using environment variables in `docker-compose.yml`:

```yaml
environment:
  - PORT=5000              # Application port
  - INSTANCE=1             # Instance identifier
  - DEBUG=False            # Debug mode (set to True for development)
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs for errors
docker-compose logs

# Verify port availability
netstat -tuln | grep -E '8080|8081|80|443'

# Remove and recreate containers
docker-compose down
docker-compose up -d --force-recreate
```

### Nginx Configuration Errors

```bash
# Test nginx configuration
docker-compose exec nginx nginx -t

# View nginx error logs
docker-compose logs nginx
```

### Application Errors

```bash
# View application logs
docker-compose logs vpn-app-1
docker-compose logs vpn-app-2

# Check health status
curl http://localhost:8080/health
curl http://localhost:8081/health
```

### DNS Issues

Ensure your domain DNS records point to your server's IP address:
```
A Record: domain1.example.com → Your_Server_IP
A Record: domain2.example.com → Your_Server_IP
```

## Production Considerations

### Security

1. **Enable HTTPS**: Always use SSL/TLS certificates in production
2. **Firewall Rules**: Only expose necessary ports (80, 443)
3. **Update Regularly**: Keep Docker images and dependencies updated
4. **Secrets Management**: Use Docker secrets or environment variables for sensitive data

### Performance

1. **Gunicorn Workers**: Adjust worker count based on CPU cores
   ```dockerfile
   CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]
   ```

2. **Nginx Caching**: Enable caching for static content
3. **Resource Limits**: Set memory and CPU limits in docker-compose.yml

### Monitoring

1. **Health Checks**: Both applications expose `/health` endpoint
2. **Logging**: Centralize logs using log aggregation tools
3. **Metrics**: Consider adding Prometheus metrics

## Backup and Recovery

```bash
# Backup configuration
tar -czf onlinevpn-backup.tar.gz nginx/ docker-compose.yml app.py

# Stop services before restoring
docker-compose down

# Restore configuration
tar -xzf onlinevpn-backup.tar.gz

# Start services
docker-compose up -d
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/BaseMax/OnlineVPN/issues
- Documentation: https://github.com/BaseMax/OnlineVPN

## License

This project is licensed under the terms specified in the LICENSE file.
