import socket
import ipaddress
import re
import logging
from urllib.parse import urlparse, urljoin, quote, unquote
from flask import Flask, request, render_template, Response, redirect, url_for, session
import requests
import urllib3

from config import PROXY_DOMAIN, SSL_VERIFY, REQUEST_TIMEOUT, PROCESSABLE_CONTENT_TYPES

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Disable SSL warnings when SSL verification is disabled
if not SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    logger.warning("SSL certificate verification is DISABLED. This may expose you to security risks.")
else:
    logger.info("SSL certificate verification is ENABLED.")

app = Flask(__name__)
app.secret_key = 'onlinevpn-secret-key-change-in-production'  # Change this in production

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


def is_domain_allowed(url, allowed_domains):
    """Check if URL's domain is in the allowed domains list"""
    if not allowed_domains:
        return False
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Check exact match or subdomain match
        for allowed in allowed_domains:
            if domain == allowed or domain.endswith('.' + allowed):
                return True
        
        return False
    except Exception:
        return False


def build_proxy_url(target_url, allowed_domains):
    """Build a proxy URL with query parameters"""
    proxy_url = f'https://{PROXY_DOMAIN}/proxy?url={quote(target_url)}'
    if allowed_domains:
        proxy_url += '&domains=' + quote(','.join(allowed_domains))
    return proxy_url


def replace_urls_in_content(content, allowed_domains, content_type, current_url):
    """
    Replace URLs in content with proxy URLs for allowed domains only.
    
    Args:
        content: The HTML/text content to process
        allowed_domains: List of domains to proxy
        content_type: MIME type of the content
        current_url: The current page URL (for resolving relative URLs)
        
    Returns:
        Modified content with replaced URLs
    """
    if not allowed_domains or not content:
        return content
    
    parsed_current = urlparse(current_url)
    current_domain = parsed_current.netloc
    
    # Replace absolute URLs for allowed domains
    for domain in allowed_domains:
        escaped_domain = re.escape(domain)
        
        # Match full URLs (http://domain.com/path or https://domain.com/path)
        pattern = r'(https?://(?:[\w\-]+\.)?' + escaped_domain + r')(/[^\s"\'\)<>]*|(?=["\'\s\)<>]|$))'
        
        def replace_absolute_url(match):
            full_domain = match.group(1)
            path = match.group(2) if match.group(2) else ''
            original_url = f'{full_domain}{path}'
            return build_proxy_url(original_url, allowed_domains)
        
        content = re.sub(pattern, replace_absolute_url, content)
        
        # Match protocol-relative URLs (//domain.com/path)
        pattern2 = r'(//(?:[\w\-]+\.)?' + escaped_domain + r')(/[^\s"\'\)<>]*|(?=["\'\s\)<>]|$))'
        
        def replace_protocol_relative(match):
            full_domain = match.group(1)
            path = match.group(2) if match.group(2) else ''
            original_url = f'https:{full_domain}{path}'
            return build_proxy_url(original_url, allowed_domains)
        
        content = re.sub(pattern2, replace_protocol_relative, content)
    
    # Replace relative URLs if current domain is in allowed list
    if current_domain in allowed_domains or any(current_domain.endswith('.' + d) for d in allowed_domains):
        # Match relative URLs in href, src, action, data attributes
        pattern3 = r'((?:href|src|action|data)=["\'])(/(?!/)[^\s"\'<>]*)'
        
        def replace_relative_url(match):
            prefix = match.group(1)
            path = match.group(2)
            # Build absolute URL
            absolute_url = urljoin(current_url, path)
            # Build proxy URL
            proxy_url = build_proxy_url(absolute_url, allowed_domains)
            return f'{prefix}{proxy_url}'
        
        content = re.sub(pattern3, replace_relative_url, content)
    
    return content


def stream_response_content(response_obj):
    """Generator function to stream response content efficiently"""
    try:
        for chunk in response_obj.iter_content(chunk_size=8192):
            yield chunk
    except Exception as e:
        logger.error(f"Error streaming content: {e}")
        raise
    finally:
        response_obj.close()


@app.route('/')
def index():
    """Render the home page"""
    return render_template('index.html')


@app.route('/proxy', methods=['GET'])
def proxy():
    """
    Main proxy route - handles all proxied requests via GET parameters.
    
    Query parameters:
        url: Target URL to proxy
        domains: Comma-separated list of domains to proxy (optional)
    """
    target_url = request.args.get('url')
    domains_param = request.args.get('domains', '')
    
    if not target_url:
        return "Error: No target URL provided. Use ?url=<target_url>&domains=<domain1,domain2>", 400
    
    # Parse domains from comma-separated list
    allowed_domains = [d.strip() for d in domains_param.split(',') if d.strip()]
    
    # Store domains in session for subsequent requests
    if allowed_domains:
        session['allowed_domains'] = allowed_domains
    elif 'allowed_domains' in session:
        # Use domains from session if not provided in URL
        allowed_domains = session['allowed_domains']
    
    # Validate URL
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
    
    # If no domains specified, add the target domain automatically
    if not allowed_domains:
        target_domain = parsed_url.netloc
        allowed_domains = [target_domain]
        session['allowed_domains'] = allowed_domains
    
    try:
        # Fetch the content from the target URL
        headers = {
            'User-Agent': request.headers.get('User-Agent', 'Mozilla/5.0 (compatible; OnlineVPN/1.0)'),
            'Accept': request.headers.get('Accept', '*/*'),
            'Accept-Encoding': request.headers.get('Accept-Encoding', 'gzip, deflate'),
            'Accept-Language': request.headers.get('Accept-Language', 'en-US,en;q=0.9'),
        }
        
        response = requests.get(
            target_url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            verify=SSL_VERIFY,
            stream=True
        )
        
        # Get content type and copy headers
        content_type = response.headers.get('content-type', 'application/octet-stream')
        
        # Copy headers that we want to preserve
        headers_to_copy = {}
        for header_name in ['Cache-Control', 'ETag', 'Last-Modified', 'Expires']:
            if header_name in response.headers:
                headers_to_copy[header_name] = response.headers[header_name]
        
        # Check if content should be processed for URL replacement
        should_process = any(ct in content_type for ct in PROCESSABLE_CONTENT_TYPES)
        
        if should_process:
            # Read and process the content
            content = response.text
            response.close()
            
            # Replace URLs with proxy URLs for allowed domains
            content = replace_urls_in_content(content, allowed_domains, content_type, target_url)
            
            # Create response
            proxy_response = Response(content, mimetype=content_type)
        else:
            # Stream binary content efficiently
            proxy_response = Response(stream_response_content(response), mimetype=content_type)
        
        # Apply headers
        for header_name, header_value in headers_to_copy.items():
            proxy_response.headers[header_name] = header_value
        
        return proxy_response
        
    except requests.RequestException as e:
        logger.error(f"Request error: {e}")
        return f"Error fetching resource: {str(e)}", 502
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        return f"Error processing request: {str(e)}", 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return {"status": "healthy"}, 200


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
