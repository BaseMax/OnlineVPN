from flask import Flask, request, render_template, Response
import requests
from urllib.parse import urlparse
import socket
import ipaddress

app = Flask(__name__)

# Blocked IP ranges to prevent SSRF attacks
BLOCKED_IP_RANGES = [
    ipaddress.ip_network('10.0.0.0/8'),      # Private network
    ipaddress.ip_network('172.16.0.0/12'),   # Private network
    ipaddress.ip_network('192.168.0.0/16'),  # Private network
    ipaddress.ip_network('127.0.0.0/8'),     # Loopback
    ipaddress.ip_network('169.254.0.0/16'),  # Link-local
    ipaddress.ip_network('::1/128'),         # IPv6 loopback
    ipaddress.ip_network('fc00::/7'),        # IPv6 private
    ipaddress.ip_network('fe80::/10'),       # IPv6 link-local
]

def is_safe_url(url):
    """Check if URL is safe to access (not targeting internal networks)"""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        
        if not hostname:
            return False
        
        # Resolve hostname to IP
        try:
            ip_str = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(ip_str)
            
            # Check if IP is in blocked ranges
            for blocked_range in BLOCKED_IP_RANGES:
                if ip in blocked_range:
                    return False
            
            return True
        except (socket.gaierror, ValueError):
            # Could not resolve hostname, reject for safety
            return False
    except Exception:
        return False

@app.route('/')
def index():
    """Render the home page with form to enter URL and domains to forward"""
    return render_template('index.html')

@app.route('/proxy', methods=['POST'])
def proxy():
    """Handle the proxy request"""
    target_url = request.form.get('target_url')
    domains_to_replace = request.form.get('domains', '').split('\n')
    domains_to_replace = [d.strip() for d in domains_to_replace if d.strip()]
    
    if not target_url:
        return "Error: No target URL provided", 400
    
    # Validate URL to prevent SSRF attacks
    try:
        parsed_url = urlparse(target_url)
        if parsed_url.scheme not in ['http', 'https']:
            return "Error: Only HTTP and HTTPS protocols are allowed", 400
        if not parsed_url.netloc:
            return "Error: Invalid URL format", 400
    except Exception:
        return "Error: Invalid URL", 400
    
    # Check if URL is safe (not targeting internal networks)
    if not is_safe_url(target_url):
        return "Error: Access to internal/private networks is not allowed", 403
    
    try:
        # Fetch the content from the target URL with proper headers
        headers = {
            'User-Agent': 'OnlineVPN-Proxy/1.0'
        }
        response = requests.get(target_url, headers=headers, timeout=30, allow_redirects=True)
        content = response.text
        
        # Replace domains in the content (basic implementation)
        # Note: This is a simple string replacement for demonstration
        # A production implementation would need more sophisticated URL rewriting
        for domain in domains_to_replace:
            if domain:
                # Replace domain references in the content
                content = content.replace(f'http://{domain}', f'http://{request.host}')
                content = content.replace(f'https://{domain}', f'http://{request.host}')
        
        return Response(content, mimetype=response.headers.get('content-type', 'text/html'))
    
    except Exception as e:
        return f"Error fetching URL: {str(e)}", 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return {"status": "healthy"}, 200

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
