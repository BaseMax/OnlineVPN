import socket
import ipaddress
import re
import logging
import base64
from urllib.parse import urlparse, urljoin

from flask import Flask, request, render_template, Response
import requests
import urllib3

from config import MIRROR_DOMAIN, SSL_VERIFY, REQUEST_TIMEOUT, PROCESSABLE_CONTENT_TYPES

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

def encode_domain(domain):
    """Encode domain for use in URL path"""
    # Use URL-safe base64 encoding
    encoded = base64.urlsafe_b64encode(domain.encode()).decode()
    # Remove padding characters for cleaner URLs
    return encoded.rstrip('=')

def decode_domain(encoded):
    """Decode domain from URL path"""
    # Add back padding if needed
    padding = (4 - len(encoded) % 4) % 4
    if padding:
        encoded += '=' * padding
    return base64.urlsafe_b64decode(encoded.encode()).decode()

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
        encoded_domain = encode_domain(domain)
        
        # Pattern 1: Match full URLs (http://domain.com/path or https://domain.com/path)
        # This pattern captures the path after the domain
        pattern1 = r'https?://' + escaped_domain + r'(/[^\s"\'\)<>]*|(?=["\'\s\)<>]|$))'
        
        def replace_full_url(match):
            path = match.group(1) if match.group(1) else ''
            # Return the proxy URL with encoded domain and path
            return f'https://{MIRROR_DOMAIN}/p/{encoded_domain}{path}'
        
        content = re.sub(pattern1, replace_full_url, content)
        
        # Pattern 2: Match protocol-relative URLs (//domain.com/path)
        pattern2 = r'//' + escaped_domain + r'(/[^\s"\'\)<>]*|(?=["\'\s\)<>]|$))'
        
        def replace_protocol_relative(match):
            path = match.group(1) if match.group(1) else ''
            return f'https://{MIRROR_DOMAIN}/p/{encoded_domain}{path}'
        
        content = re.sub(pattern2, replace_protocol_relative, content)
    
    # Pattern 3: Handle relative URLs that start with / (not //)
    # Only process if we have a base_url and domains to match against
    if base_url and domains:
        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc
        
        # Only replace relative URLs if the base domain is in our domains list
        if is_domain_match(base_domain, domains):
            encoded_base_domain = encode_domain(base_domain)
            # Match relative URLs: /path but not // (protocol-relative)
            # Look for href="/path", src="/path", etc.
            # Pattern matches: attribute="/path" where path doesn't start with another /
            pattern3 = r'((?:href|src|action|data)=["\'])(/(?!/)[^\s"\'<>]*)'
            
            def replace_relative_url(match):
                prefix = match.group(1)  # The attribute and opening quote
                path = match.group(2)     # The relative path
                return f'{prefix}https://{MIRROR_DOMAIN}/p/{encoded_base_domain}{path}'
            
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
        response = requests.get(target_url, headers=headers, timeout=30, allow_redirects=True, verify=SSL_VERIFY)
        content = response.text
        
        # Get content type
        content_type = response.headers.get('content-type', 'text/html')
        
        # Replace URLs in the content using the new function
        # Pass the target_url as base_url to handle relative paths
        content = replace_urls_in_content(content, domains_to_replace, content_type, base_url=target_url)
        
        return Response(content, mimetype=content_type)
    
    except Exception as e:
        return f"Error fetching URL: {str(e)}", 500

@app.route('/p/<path:encoded_domain_and_path>')
def proxy_resource(encoded_domain_and_path):
    """
    Proxy route that handles all resource requests.
    URL format: /p/<encoded_domain>/<path>
    Example: /p/eW91dHViZS5jb20/watch?v=123
    """
    try:
        # Split the encoded domain from the path
        parts = encoded_domain_and_path.split('/', 1)
        encoded_domain = parts[0]
        
        if not encoded_domain:
            return "Error: Invalid proxy URL format", 400
        
        resource_path = '/' + parts[1] if len(parts) > 1 else ''
        
        # Decode the domain
        try:
            original_domain = decode_domain(encoded_domain)
        except Exception as e:
            logger.error(f"Failed to decode domain '{encoded_domain}': {e}")
            return "Error: Invalid encoded domain", 400
        
        # Construct the original URL
        original_url = f'https://{original_domain}{resource_path}'
        
        # Add query string if present
        if request.query_string:
            original_url += '?' + request.query_string.decode()
        
        logger.info(f"Proxying request: {original_url}")
        
        # Validate URL to prevent SSRF attacks
        if not is_safe_url(original_url):
            return "Error: Access to internal/private networks is not allowed", 403
        
        # Fetch the content from the original URL
        headers = {
            'User-Agent': request.headers.get('User-Agent', 'OnlineVPN-Proxy/1.0'),
            'Accept': request.headers.get('Accept', '*/*'),
            'Accept-Encoding': request.headers.get('Accept-Encoding', 'gzip, deflate'),
            'Accept-Language': request.headers.get('Accept-Language', 'en-US,en;q=0.9'),
        }
        
        response = requests.get(
            original_url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            verify=SSL_VERIFY,
            stream=True
        )
        
        try:
            # Get content type and copy relevant headers before processing content
            content_type = response.headers.get('content-type', 'application/octet-stream')
            
            # Copy headers that we want to preserve (before response is closed)
            headers_to_copy = {}
            for header_name in ['Cache-Control', 'ETag', 'Last-Modified', 'Expires']:
                if header_name in response.headers:
                    headers_to_copy[header_name] = response.headers[header_name]
            
            # Check if content should be processed for URL replacement
            should_process = any(ct in content_type for ct in PROCESSABLE_CONTENT_TYPES)
            
            if should_process:
                # Read and process the content
                content = response.text
                # Close response since we've read all content
                response.close()
                
                # Replace URLs with the original domain in the list
                content = replace_urls_in_content(content, [original_domain], content_type, base_url=original_url)
                
                # Create response with processed content
                proxy_response = Response(content, mimetype=content_type)
            else:
                # Stream binary content efficiently without loading into memory
                # Create a generator that properly manages the response lifecycle
                def generate(resp):
                    try:
                        for chunk in resp.iter_content(chunk_size=8192):
                            yield chunk
                    except Exception as e:
                        logger.error(f"Error streaming content: {e}")
                        raise
                    finally:
                        resp.close()
                
                proxy_response = Response(generate(response), mimetype=content_type)
            
            # Apply the headers we copied earlier
            for header_name, header_value in headers_to_copy.items():
                proxy_response.headers[header_name] = header_value
            
            return proxy_response
        except Exception:
            # Ensure response is closed if an error occurs
            response.close()
            raise
    
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
