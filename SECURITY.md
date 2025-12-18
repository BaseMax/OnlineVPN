# Security Considerations for OnlineVPN

## Overview

OnlineVPN is a web-based proxy application that by design makes HTTP requests to user-provided URLs. While this is the core functionality, we have implemented multiple layers of security to protect against abuse.

## SSRF (Server-Side Request Forgery) Protection

### The Nature of the Application

**Important:** OnlineVPN is designed to act as a proxy, which means it intentionally makes HTTP requests to user-provided URLs. This is the primary feature of the application, not a vulnerability.

### Implemented Protections

Despite the inherent risk, we have implemented comprehensive SSRF protections:

#### 1. Protocol Validation
- **Only HTTP and HTTPS allowed**: File://, ftp://, gopher://, and other protocols are blocked
- Prevents protocol smuggling attacks

#### 2. IP Range Blocking
The application blocks requests to internal/private networks:

**IPv4 Blocked Ranges:**
- `10.0.0.0/8` - Private network
- `172.16.0.0/12` - Private network  
- `192.168.0.0/16` - Private network
- `127.0.0.0/8` - Loopback addresses
- `169.254.0.0/16` - Link-local addresses

**IPv6 Blocked Ranges:**
- `::1/128` - Loopback
- `fc00::/7` - Unique local addresses (private)
- `fe80::/10` - Link-local addresses

#### 3. DNS Resolution Validation
- All hostnames are resolved to IP addresses before making requests
- Resolved IPs are checked against blocked ranges
- Prevents DNS rebinding attacks

#### 4. Request Timeouts
- All proxy requests have a 30-second timeout
- Prevents resource exhaustion from slow endpoints

#### 5. User-Agent Header
- All requests include a identifying User-Agent: `OnlineVPN-Proxy/1.0`
- Allows target servers to identify and potentially block proxy traffic if desired

## CodeQL Alert: py/full-ssrf

### Alert Details
```
The full URL of this request depends on a user-provided value
Location: app.py:81
```

### Why This Is Acceptable

This CodeQL alert is **acknowledged and accepted** because:

1. **By Design**: The application's purpose is to proxy user-provided URLs
2. **Mitigated**: Multiple layers of protection prevent access to internal resources
3. **Documented**: This security consideration is clearly documented
4. **Validated**: All user inputs are validated before use

### Residual Risk

Users should understand that deploying a public proxy service carries inherent risks:

- **Resource Consumption**: Malicious users could consume bandwidth/resources
- **Legal Liability**: Proxied traffic originates from your server
- **Abuse Potential**: May be used to bypass access controls

## Additional Security Measures

### Docker Security

1. **Non-root User**: Application runs as non-root user `appuser` (UID 1000)
2. **Minimal Base Image**: Uses `python:3.11-slim` to reduce attack surface
3. **No Privileged Containers**: Containers run without elevated privileges
4. **Network Isolation**: Services communicate through dedicated Docker network

### Nginx Security

1. **Request Timeouts**: Configured with appropriate timeout values (120s)
2. **Buffer Limits**: Configured buffer sizes prevent memory exhaustion
3. **SSL/TLS Ready**: Configuration supports HTTPS with modern protocols
4. **Header Forwarding**: Proper X-Forwarded-For headers for request tracking

## Production Deployment Recommendations

### 1. Enable HTTPS

Always use SSL/TLS certificates in production:

```bash
# Using Let's Encrypt
certbot certonly --standalone -d your-domain.com
```

Update nginx configuration with certificate paths.

### 2. Rate Limiting

Implement rate limiting to prevent abuse:

```nginx
# In nginx.conf
http {
    limit_req_zone $binary_remote_addr zone=proxy_limit:10m rate=10r/s;
    
    server {
        location /proxy {
            limit_req zone=proxy_limit burst=20 nodelay;
            # ... other settings
        }
    }
}
```

### 3. Authentication

Add authentication to restrict access:

```nginx
# Basic auth example
server {
    auth_basic "Restricted Access";
    auth_basic_user_file /etc/nginx/.htpasswd;
    # ... other settings
}
```

Or implement application-level authentication in Flask.

### 4. Logging and Monitoring

- **Enable access logs**: Track all proxy requests
- **Monitor for abuse**: Watch for unusual patterns
- **Set up alerts**: Get notified of suspicious activity

```bash
# Monitor logs in real-time
docker compose logs -f vpn-app-1 | grep -i error
```

### 5. Firewall Configuration

Only expose necessary ports:

```bash
# Using ufw (Ubuntu)
ufw allow 80/tcp
ufw allow 443/tcp
ufw deny 8080/tcp  # Block direct access to app instances
ufw deny 8081/tcp
```

### 6. Regular Updates

Keep all components updated:

```bash
# Update Docker images
docker compose pull
docker compose up -d

# Update system packages
apt update && apt upgrade
```

### 7. Resource Limits

Set resource limits in docker-compose.yml:

```yaml
services:
  vpn-app-1:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

## Incident Response

If you detect abuse:

1. **Check logs** for suspicious activity:
   ```bash
   docker compose logs vpn-app-1 | grep -E "Error|failed"
   ```

2. **Block offending IPs** in nginx:
   ```nginx
   deny 1.2.3.4;
   ```

3. **Restart services** if needed:
   ```bash
   docker compose restart
   ```

4. **Review and enhance** security measures

## Legal Considerations

### Important Notice

⚠️ **By deploying this proxy service, you acknowledge:**

- All proxied traffic originates from your server/IP address
- You may be held liable for traffic proxied through your service
- You should comply with applicable laws and regulations
- You should implement appropriate access controls and monitoring

### Recommended Actions

1. **Terms of Service**: Create and display terms of service
2. **Acceptable Use Policy**: Define what is and isn't allowed
3. **User Authentication**: Require authentication to track usage
4. **Logging**: Maintain logs for accountability (following data protection laws)
5. **Abuse Contact**: Provide contact information for abuse reports

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do NOT** open a public GitHub issue
2. Email security concerns to the repository maintainer
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

## Security Checklist for Deployment

Before deploying to production:

- [ ] HTTPS enabled with valid SSL/TLS certificates
- [ ] Rate limiting configured
- [ ] Authentication implemented
- [ ] Firewall rules configured
- [ ] Resource limits set
- [ ] Logging enabled and monitored
- [ ] Backup strategy in place
- [ ] Incident response plan documented
- [ ] Legal/compliance review completed
- [ ] Regular update schedule established

## Conclusion

While OnlineVPN implements robust security measures against SSRF and other attacks, deploying a public proxy service carries inherent risks. Administrators must:

1. Understand the security implications
2. Implement additional protections as needed
3. Monitor for abuse
4. Keep the system updated
5. Comply with legal requirements

**The SSRF CodeQL alert is acknowledged as an intentional design choice with appropriate mitigations in place.**

## References

- [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [Nginx Security Controls](https://nginx.org/en/docs/http/ngx_http_core_module.html#client_max_body_size)

---

**Last Updated:** 2025-12-18  
**Version:** 1.0
