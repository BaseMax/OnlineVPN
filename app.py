import socket
import ipaddress
import re
import logging
from urllib.parse import urlparse, urljoin, quote, unquote
from flask import Flask, request, render_template, Response, redirect, make_response
import requests
import urllib3

from config import PROXY_DOMAIN, SSL_VERIFY, REQUEST_TIMEOUT, PROCESSABLE_CONTENT_TYPES

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    logger.warning("SSL verification DISABLED")

# ------------------------------------------------------------------------------
# Flask app
# ------------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = 'onlinevpn-secret-key-change-in-production'

# ------------------------------------------------------------------------------
# SSRF protection
# ------------------------------------------------------------------------------

BLOCKED_IP_RANGES = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fc00::/7'),
    ipaddress.ip_network('fe80::/10'),
]


def is_safe_url(url: str) -> bool:
    """Check if URL doesn't point to internal network"""
    try:
        parsed = urlparse(url)
        if not parsed.hostname:
            return False
        ip = ipaddress.ip_address(socket.gethostbyname(parsed.hostname))
        return not any(ip in net for net in BLOCKED_IP_RANGES)
    except Exception:
        return False


# ------------------------------------------------------------------------------
# Cookie helpers
# ------------------------------------------------------------------------------

def get_base_url(full_url: str) -> str:
    """Extract base URL (scheme + netloc) from full URL"""
    parsed = urlparse(full_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def get_path_from_url(full_url: str) -> str:
    """Extract path from full URL"""
    parsed = urlparse(full_url)
    path = parsed.path or '/'
    if parsed.query:
        path += f"?{parsed.query}"
    return path


def set_cookies(response, base_url: str, domains: list):
    """Set base URL and allowed domains in cookies"""
    response.set_cookie('base_url', base_url, max_age=3600*24)
    response.set_cookie('allowed_domains', ','.join(domains), max_age=3600*24)
    return response


def get_cookies():
    """Get base URL and allowed domains from cookies"""
    base_url = request.cookies.get('base_url', '')
    domains_str = request.cookies.get('allowed_domains', '')
    domains = [d.strip() for d in domains_str.split(',') if d.strip()]
    return base_url, domains


# ------------------------------------------------------------------------------
# URL replacement helpers
# ------------------------------------------------------------------------------

def replace_absolute_urls(content: str, domains: list, proxy_base: str) -> str:
    """Replace absolute URLs (http://, https://) in content"""
    if not domains:
        return content
    for domain in domains:
        escaped = re.escape(domain)
        pattern = rf'(https?://(?:[\w\-]+\.)?{escaped})'
        content = re.sub(pattern, proxy_base, content)
    return content


def replace_protocol_relative(content: str, domains: list, proxy_base: str) -> str:
    """Replace protocol-relative URLs (//) in content"""
    if not domains:
        return content
    proxy_no_scheme = proxy_base.replace('https:', '').replace('http:', '')
    for domain in domains:
        escaped = re.escape(domain)
        pattern = rf'//(?:[\w\-]+\.)?{escaped}'
        content = re.sub(pattern, proxy_no_scheme, content)
    return content


def replace_relative_urls(content: str, base_url: str, proxy_base: str) -> str:
    """Replace relative URLs (/, ./) in content"""
    # Replace src="/path" and href="/path" but not "//"
    content = re.sub(
        r'((?:href|src|action)=["\'])(/(?!/)[^"\'>]+)',
        rf'\1{proxy_base}\2',
        content
    )
    # Replace src="./path" and href="./path"
    content = re.sub(
        r'((?:href|src|action)=["\'])(\.\/[^"\'>]+)',
        rf'\1{proxy_base}/\2',
        content
    )
    return content


def rewrite_content(content: str, base_url: str, domains: list) -> str:
    """Apply all URL replacements to content"""
    proxy_base = f"https://{PROXY_DOMAIN}"
    # First replace relative URLs to avoid conflicts
    content = replace_relative_urls(content, base_url, proxy_base)
    # Then replace protocol-relative URLs
    content = replace_protocol_relative(content, domains, proxy_base)
    # Finally replace absolute URLs
    content = replace_absolute_urls(content, domains, proxy_base)
    return content


# ------------------------------------------------------------------------------
# Request forwarding helpers
# ------------------------------------------------------------------------------

def copy_request_headers() -> dict:
    """Copy relevant headers from incoming request"""
    headers = {}
    skip_headers = {'host', 'cookie', 'content-length', 'content-encoding'}
    for key, value in request.headers:
        if key.lower() not in skip_headers:
            headers[key] = value
    if 'Accept-Encoding' not in headers:
        headers['Accept-Encoding'] = 'identity'
    return headers


def forward_request(target_url: str, method: str) -> requests.Response:
    """Forward request to target URL with same method and data"""
    headers = copy_request_headers()
    data = request.get_data() if request.data else None
    return requests.request(
        method=method,
        url=target_url,
        headers=headers,
        data=data,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=False,
        verify=SSL_VERIFY,
    )


def should_process_content(content_type: str) -> bool:
    """Check if content type should be processed for URL replacement"""
    return any(ct in content_type.lower() for ct in PROCESSABLE_CONTENT_TYPES)


def create_response(upstream_resp, base_url: str, domains: list):
    """Create Flask response from upstream response"""
    content_type = upstream_resp.headers.get('Content-Type', '').lower()
    if should_process_content(content_type):
        text = upstream_resp.text
        text = rewrite_content(text, base_url, domains)
        resp = Response(text, status=upstream_resp.status_code)
        resp.headers['Content-Type'] = content_type
    else:
        resp = Response(upstream_resp.content, status=upstream_resp.status_code)
        if content_type:
            resp.headers['Content-Type'] = content_type
    return resp


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------

@app.route('/maxme', methods=['GET', 'POST'])
def setup_proxy():
    """Show form and handle proxy setup"""
    if request.method == 'GET':
        return render_template('index.html')
    
    target_url = request.form.get('target_url', '').strip()
    domains_input = request.form.get('domains', '').strip()
    
    if not target_url:
        return "Missing target URL", 400
    
    parsed = urlparse(target_url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return "Invalid URL", 400
    
    if not is_safe_url(target_url):
        return "Blocked internal address", 403
    
    base_url = get_base_url(target_url)
    path = get_path_from_url(target_url)
    
    domains = [d.strip() for d in domains_input.split(',') if d.strip()]
    if not domains:
        domains = [parsed.netloc]
    
    resp = make_response(redirect(path))
    set_cookies(resp, base_url, domains)
    return resp


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def proxy_request(path):
    """Handle all requests and proxy to target"""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        resp = Response('', status=200)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = '*'
        return resp
    
    base_url, domains = get_cookies()
    
    if not base_url:
        return redirect('/maxme')
    
    # Build target URL
    if path:
        target_url = f"{base_url}/{path}"
    else:
        target_url = base_url
    
    if request.query_string:
        target_url += f"?{request.query_string.decode()}"
    
    try:
        upstream_resp = forward_request(target_url, request.method)
        resp = create_response(upstream_resp, base_url, domains)
        
        # Add CORS headers
        resp.headers['Access-Control-Allow-Origin'] = '*'
        
        # Handle redirects
        if 300 <= upstream_resp.status_code < 400:
            location = upstream_resp.headers.get('Location')
            if location:
                # Rewrite redirect location
                parsed_loc = urlparse(location)
                if parsed_loc.netloc in domains or not parsed_loc.netloc:
                    new_path = parsed_loc.path or '/'
                    if parsed_loc.query:
                        new_path += f"?{parsed_loc.query}"
                    resp.headers['Location'] = new_path
                else:
                    resp.headers['Location'] = location
        
        return resp
        
    except requests.RequestException as e:
        logger.exception("Upstream request failed")
        return f"Upstream error: {e}", 502


@app.route('/health')
def health():
    """Health check endpoint"""
    return {"status": "ok"}, 200


# ------------------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
