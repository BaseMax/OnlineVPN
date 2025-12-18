from flask import Flask, request, render_template, Response
import requests
from urllib.parse import urlparse, urljoin
import socket
import ipaddress
import re
from config import MIRROR_DOMAIN

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

def is_domain_match(base_domain, domains):
    """
    Check if base_domain matches any domain in the domains list.
    Handles exact matches and subdomain relationships.
    
    Args:
        base_domain: The domain to check (e.g., "www.example.com")
        domains: List of domains to match against
        
    Returns:
        True if base_domain matches any domain in the list
    """
    if base_domain in domains:
        return True
    
    for domain in domains:
        # Check if base_domain is a subdomain of domain or vice versa
        if base_domain.endswith('.' + domain) or domain.endswith('.' + base_domain):
            return True
    
    return False

def replace_urls_in_content(content, domains, content_type, base_url=None):
    """
    Replace URLs in content with proxy URLs.
    
    Args:
        content: The HTML/text content to process
        domains: List of domains to replace
        content_type: MIME type of the content
        base_url: The base URL of the proxied page (for handling relative URLs)
        
    Returns:
        Modified content with replaced URLs
    """
    if not domains:
        return content
    
    # Create a regex pattern for matching URLs with specified domains
    for domain in domains:
        if not domain:
            continue
            
        # Escape special regex characters in domain
        escaped_domain = re.escape(domain)
        
        # Pattern 1: Match full URLs (http://domain.com/path or https://domain.com/path)
        # This pattern captures the path after the domain
        pattern1 = r'https?://' + escaped_domain + r'(/[^\s"\'\)<>]*|(?=["\'\s\)<>]|$))'
        
        def replace_full_url(match):
            path = match.group(1) if match.group(1) else ''
            # Return the proxy URL with the path
            return f'https://{MIRROR_DOMAIN}{path}'
        
        content = re.sub(pattern1, replace_full_url, content)
        
        # Pattern 2: Match protocol-relative URLs (//domain.com/path)
        pattern2 = r'//' + escaped_domain + r'(/[^\s"\'\)<>]*|(?=["\'\s\)<>]|$))'
        
        def replace_protocol_relative(match):
            path = match.group(1) if match.group(1) else ''
            return f'https://{MIRROR_DOMAIN}{path}'
        
        content = re.sub(pattern2, replace_protocol_relative, content)
    
    # Pattern 3: Handle relative URLs that start with / (not //)
    # Only process if we have a base_url and domains to match against
    if base_url and domains:
        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc
        
        # Only replace relative URLs if the base domain is in our domains list
        if is_domain_match(base_domain, domains):
            # Match relative URLs: /path but not // (protocol-relative)
            # Look for href="/path", src="/path", etc.
            # Pattern matches: attribute="/path" where path doesn't start with another /
            pattern3 = r'((?:href|src|action|data)=["\'])(/(?!/)[^\s"\'<>]*)'
            
            def replace_relative_url(match):
                prefix = match.group(1)  # The attribute and opening quote
                path = match.group(2)     # The relative path
                return f'{prefix}https://{MIRROR_DOMAIN}{path}'
            
            content = re.sub(pattern3, replace_relative_url, content)
    
    return content

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
        
        # Get content type
        content_type = response.headers.get('content-type', 'text/html')
        
        # Replace URLs in the content using the new function
        # Pass the target_url as base_url to handle relative paths
        content = replace_urls_in_content(content, domains_to_replace, content_type, base_url=target_url)
        
        return Response(content, mimetype=content_type)
    
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
