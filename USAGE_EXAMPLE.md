# OnlineVPN Usage Examples

This document provides practical examples of deploying and using the OnlineVPN application.

## Deployment Scenarios

### Scenario 1: Basic Local Deployment

Deploy two instances accessible on localhost:

```bash
# Start services
docker compose up -d

# Access instances directly
curl http://localhost:8080/health
curl http://localhost:8081/health

# View logs
docker compose logs -f vpn-app-1
docker compose logs -f vpn-app-2
```

### Scenario 2: Production Deployment with Two Domains

Example: Deploy `vpn1.mycompany.com` and `vpn2.mycompany.com`

**Step 1: Configure DNS**
```
A Record: vpn1.mycompany.com → Your_Server_IP
A Record: vpn2.mycompany.com → Your_Server_IP
```

**Step 2: Update Nginx Configuration**

Edit `nginx/conf.d/vpn-app-1.conf`:
```nginx
server_name vpn1.mycompany.com;
```

Edit `nginx/conf.d/vpn-app-2.conf`:
```nginx
server_name vpn2.mycompany.com;
```

**Step 3: Deploy**
```bash
docker compose up -d
```

**Step 4: Access**
- https://vpn1.mycompany.com → Instance 1
- https://vpn2.mycompany.com → Instance 2

### Scenario 3: Development vs Production

Use different configurations for dev and prod:

**docker-compose.dev.yml**
```yaml
version: '3.8'
services:
  vpn-app-1:
    build: .
    ports:
      - "8080:5000"
    environment:
      - DEBUG=True
      - INSTANCE=1
```

**docker-compose.prod.yml**
```yaml
version: '3.8'
services:
  vpn-app-1:
    build: .
    ports:
      - "8080:5000"
    environment:
      - DEBUG=False
      - INSTANCE=1
    restart: always
```

Deploy development:
```bash
docker compose -f docker-compose.dev.yml up
```

Deploy production:
```bash
docker compose -f docker-compose.prod.yml up -d
```

## Using the VPN Proxy

### Example 1: Basic Web Page Access

1. Open the application in your browser
2. Enter target URL: `https://example.com`
3. Leave domains field empty
4. Click "Access via Proxy"

The page will be fetched through the proxy server.

### Example 2: Domain Forwarding

Access a page and forward specific domains through the proxy:

**Form Input:**
- Target URL: `https://news.example.com`
- Domains to forward:
  ```
  cdn.example.com
  static.example.com
  api.example.com
  ```

The proxy will:
1. Fetch the page from `news.example.com`
2. Replace references to the listed domains
3. Forward requests for those domains through the proxy

### Example 3: Multiple Subdomain Forwarding

**Use Case:** Access a web application that uses multiple subdomains

- Target URL: `https://app.example.com`
- Domains to forward:
  ```
  app.example.com
  api.example.com
  cdn.example.com
  assets.example.com
  images.example.com
  ```

## Load Balancing Examples

### Round-Robin with Nginx

Configure Nginx to load balance across both instances:

Create `nginx/conf.d/loadbalancer.conf`:
```nginx
upstream vpn_backend {
    server vpn-app-1:5000;
    server vpn-app-2:5000;
}

server {
    listen 80;
    server_name vpn.mycompany.com;

    location / {
        proxy_pass http://vpn_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Geographic Distribution

Route traffic based on geographic location:

```nginx
geo $vpn_backend {
    default vpn_app_1;
    # US traffic
    1.0.0.0/8 vpn_app_1;
    # EU traffic  
    2.0.0.0/8 vpn_app_2;
}

upstream vpn_app_1 {
    server vpn-app-1:5000;
}

upstream vpn_app_2 {
    server vpn-app-2:5000;
}

server {
    listen 80;
    server_name vpn.example.com;

    location / {
        proxy_pass http://$vpn_backend;
        # ... other proxy settings
    }
}
```

## Monitoring Examples

### Health Check Monitoring

Create a monitoring script:

```bash
#!/bin/bash
# health-check.sh

check_instance() {
    local url=$1
    local name=$2
    
    if curl -f -s -o /dev/null "$url/health"; then
        echo "✓ $name is healthy"
    else
        echo "✗ $name is unhealthy"
        # Send alert
        # mail -s "Alert: $name down" admin@example.com
    fi
}

check_instance "http://localhost:8080" "VPN Instance 1"
check_instance "http://localhost:8081" "VPN Instance 2"
```

Run periodically with cron:
```bash
*/5 * * * * /path/to/health-check.sh
```

### Log Aggregation

Collect logs from both instances:

```bash
# Real-time monitoring
docker compose logs -f --tail=100 vpn-app-1 vpn-app-2

# Save logs to file
docker compose logs --no-color vpn-app-1 > /var/log/vpn-app-1.log
docker compose logs --no-color vpn-app-2 > /var/log/vpn-app-2.log

# Monitor nginx access
docker compose exec nginx tail -f /var/log/nginx/access.log
```

## Security Examples

### SSL/TLS Configuration with Let's Encrypt

**Step 1: Install Certbot**
```bash
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx
```

**Step 2: Obtain Certificates**
```bash
# Stop nginx temporarily
docker compose stop nginx

# Get certificates
sudo certbot certonly --standalone \
    -d vpn1.mycompany.com \
    -d vpn2.mycompany.com

# Restart nginx
docker compose start nginx
```

**Step 3: Update docker-compose.yml**
```yaml
nginx:
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./nginx/conf.d:/etc/nginx/conf.d:ro
    - /etc/letsencrypt:/etc/letsencrypt:ro
```

**Step 4: Enable HTTPS in Nginx Config**

Uncomment HTTPS blocks in `nginx/conf.d/vpn-app-1.conf` and `vpn-app-2.conf`, then update certificate paths:

```nginx
ssl_certificate /etc/letsencrypt/live/vpn1.mycompany.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/vpn1.mycompany.com/privkey.pem;
```

**Step 5: Restart Services**
```bash
docker compose restart nginx
```

### Auto-renewal Setup

```bash
# Add to crontab
0 3 * * * certbot renew --quiet && docker compose restart nginx
```

## Scaling Examples

### Adding a Third Instance

**Step 1: Update docker-compose.yml**
```yaml
vpn-app-3:
  build: .
  container_name: onlinevpn-app-3
  ports:
    - "8082:5000"
  environment:
    - PORT=5000
    - INSTANCE=3
  restart: unless-stopped
  networks:
    - vpn-network
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
```

**Step 2: Create nginx configuration**

Create `nginx/conf.d/vpn-app-3.conf` for the third domain.

**Step 3: Deploy**
```bash
docker compose up -d
```

## Backup and Recovery

### Backup Configuration

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/onlinevpn"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup configuration files
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" \
    nginx/ \
    docker-compose.yml \
    Dockerfile \
    requirements.txt \
    app.py \
    templates/

echo "Backup created: $BACKUP_DIR/config_$DATE.tar.gz"
```

### Restore Configuration

```bash
# Extract backup
tar -xzf config_20240101_120000.tar.gz

# Restart services
docker compose down
docker compose up -d
```

## Troubleshooting Examples

### Issue: Container Won't Start

```bash
# Check logs
docker compose logs vpn-app-1

# Check container status
docker compose ps

# Inspect container
docker inspect onlinevpn-app-1

# Restart specific service
docker compose restart vpn-app-1
```

### Issue: High Memory Usage

```bash
# Check resource usage
docker stats

# Limit resources in docker-compose.yml
services:
  vpn-app-1:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
```

### Issue: Nginx Configuration Error

```bash
# Test nginx configuration
docker compose exec nginx nginx -t

# View nginx error log
docker compose logs nginx | grep error

# Reload nginx configuration
docker compose exec nginx nginx -s reload
```

## Performance Tuning

### Gunicorn Workers

Adjust workers based on CPU cores:

```dockerfile
# In Dockerfile, for 4 CPU cores
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "9", "app:app"]
# Formula: (2 x CPU_CORES) + 1 = (2 x 4) + 1 = 9
```

### Nginx Caching

Add caching for better performance:

```nginx
# In nginx.conf
http {
    proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=vpn_cache:10m max_size=1g inactive=60m;
    
    server {
        location / {
            proxy_cache vpn_cache;
            proxy_cache_valid 200 10m;
            proxy_cache_valid 404 1m;
            # ... other settings
        }
    }
}
```

## Integration Examples

### With Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml vpn

# Scale service
docker service scale vpn_vpn-app-1=3

# Check services
docker service ls
```

### With Kubernetes

Convert docker-compose to Kubernetes manifests using kompose:

```bash
kompose convert -f docker-compose.yml

# Apply to cluster
kubectl apply -f .
```

## Conclusion

These examples cover common deployment scenarios and configurations. Adapt them to your specific requirements and infrastructure.

For more information, see [DEPLOYMENT.md](DEPLOYMENT.md) and [README.md](README.md).
