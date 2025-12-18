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


def get_ip_from_url(url: str):
    """Extract IP address from URL hostname"""
    parsed = urlparse(url)
    if not parsed.hostname:
        return None
    return socket.gethostbyname(parsed.hostname)


def is_ip_blocked(ip_str: str) -> bool:
    """Check if IP is in blocked ranges"""
    ip = ipaddress.ip_address(ip_str)
    return any(ip in net for net in BLOCKED_IP_RANGES)


def is_safe_url(url: str) -> bool:
    """Check if URL doesn't point to internal network"""
    try:
        ip_str = get_ip_from_url(url)
        return ip_str and not is_ip_blocked(ip_str)
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


def parse_domains_string(domains_str: str) -> list:
    """Parse comma-separated domains string"""
    return [d.strip() for d in domains_str.split(',') if d.strip()]


def get_cookies():
    """Get base URL and allowed domains from cookies"""
    base_url = request.cookies.get('base_url', '')
    domains = parse_domains_string(request.cookies.get('allowed_domains', ''))
    return base_url, domains


# ------------------------------------------------------------------------------
# URL replacement helpers
# ------------------------------------------------------------------------------
def replace_domain_in_content(content: str, domain: str, proxy_base: str) -> str:
    """Replace single domain with proxy base"""
    escaped = re.escape(domain)
    pattern = rf'(https?://(?:[\w\-]+\.)?{escaped})(/[^\s"\'<>]*)?'
    def repl(m):
        return proxy_base + (m.group(2) if m.group(2) else '')
    return re.sub(pattern, repl, content)


def replace_absolute_urls(content: str, domains: list, proxy_base: str) -> str:
    """Replace absolute URLs (http://, https://) in content"""
    if not domains:
        return content
    for domain in domains:
        content = replace_domain_in_content(content, domain, proxy_base)
    return content


def remove_scheme(url: str) -> str:
    """Remove http/https scheme from URL"""
    parsed = urlparse(url)
    return f"//{parsed.netloc}{parsed.path}"


def replace_protocol_rel_domain(content: str, domain: str, proxy_base: str) -> str:
    """Replace protocol-relative domain"""
    escaped = re.escape(domain)
    pattern = rf'//(?:[\w\-]+\.)?{escaped}'
    return re.sub(pattern, remove_scheme(proxy_base), content)


def replace_protocol_relative(content: str, domains: list, proxy_base: str) -> str:
    """Replace protocol-relative URLs (//) in content"""
    if not domains:
        return content
    for domain in domains:
        content = replace_protocol_rel_domain(content, domain, proxy_base)
    return content


def replace_slash_paths(content: str, proxy_base: str) -> str:
    """Replace /path style URLs"""
    pattern = r'((?:href|src|action)=["\'])(/(?!/)[^"\'>]+)'
    return re.sub(pattern, rf'\1{proxy_base}\2', content)


def replace_dot_paths(content: str, proxy_base: str) -> str:
    """Replace ./path style URLs"""
    pattern = r'((?:href|src|action)=["\'])\.\/([^"\'>]+)'
    return re.sub(pattern, rf'\1{proxy_base}/\2', content)


def replace_relative_urls(content: str, base_url: str, proxy_base: str) -> str:
    """Replace relative URLs (/, ./) in content"""
    content = replace_slash_paths(content, proxy_base)
    content = replace_dot_paths(content, proxy_base)
    return content


def get_proxy_base() -> str:
    """Get proxy base URL"""
    return f"https://{PROXY_DOMAIN}"


def rewrite_content(content: str, base_url: str, domains: list) -> str:
    """Apply all URL replacements to content"""
    proxy_base = get_proxy_base()
    content = replace_relative_urls(content, base_url, proxy_base)
    content = replace_protocol_relative(content, domains, proxy_base)
    return replace_absolute_urls(content, domains, proxy_base)


# ------------------------------------------------------------------------------
# Request forwarding helpers
# ------------------------------------------------------------------------------
def should_skip_header(key: str) -> bool:
    """Check if header should be skipped"""
    skip = {'host', 'cookie', 'content-length', 'content-encoding'}
    return key.lower() in skip


def copy_request_headers() -> dict:
    """Copy relevant headers from incoming request"""
    headers = {k: v for k, v in request.headers if not should_skip_header(k)}
    # if 'Accept-Encoding' not in headers:
    #     headers['Accept-Encoding'] = 'identity'
    headers['Accept-Encoding'] = 'identity'
    return headers


def get_request_data():
    """Get request body data"""
    return request.get_data() if request.data else None


def forward_request(target_url: str, method: str) -> requests.Response:
    """Forward request to target URL with same method and data"""
    return requests.request(
        method=method, url=target_url, headers=copy_request_headers(),
        data=get_request_data(), timeout=REQUEST_TIMEOUT,
        allow_redirects=False, verify=SSL_VERIFY
    )


def should_process_content(content_type: str) -> bool:
    """Check if content type should be processed for URL replacement"""
    return any(ct in content_type.lower() for ct in PROCESSABLE_CONTENT_TYPES)


def create_text_response(upstream_resp, base_url: str, domains: list):
    """Create response for text content"""
    text = rewrite_content(upstream_resp.text, base_url, domains)
    resp = Response(text, status=upstream_resp.status_code)
    content_type = upstream_resp.headers.get('Content-Type', '')
    resp.headers['Content-Type'] = content_type
    return resp


def create_binary_response(upstream_resp):
    """Create response for binary content"""
    resp = Response(upstream_resp.content, status=upstream_resp.status_code)
    content_type = upstream_resp.headers.get('Content-Type', '')
    if content_type:
        resp.headers['Content-Type'] = content_type
    return resp


def create_response(upstream_resp, base_url: str, domains: list):
    """Create Flask response from upstream response"""
    ct = upstream_resp.headers.get('Content-Type', '').lower()
    if should_process_content(ct):
        return create_text_response(upstream_resp, base_url, domains)
    return create_binary_response(upstream_resp)


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------
def validate_url(target_url: str) -> tuple:
    """Validate URL format and safety"""
    if not target_url:
        return False, "Missing target URL"
    parsed = urlparse(target_url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return False, "Invalid URL"
    return (True, None) if is_safe_url(target_url) else (False, "Blocked internal address")


def get_domains_from_input(domains_input: str, default_domain: str) -> list:
    """Parse domains from input or use default"""
    domains = parse_domains_string(domains_input)
    return domains if domains else [default_domain]


def handle_setup_post():
    """Handle POST request for proxy setup"""
    target_url = request.form.get('target_url', '').strip()
    valid, error = validate_url(target_url)
    if not valid:
        return error, 400 if "Missing" in error else 403
    parsed = urlparse(target_url)
    domains = get_domains_from_input(request.form.get('domains', '').strip(), parsed.netloc)
    resp = make_response(redirect(get_path_from_url(target_url)))
    return set_cookies(resp, get_base_url(target_url), domains)


@app.route('/maxme', methods=['GET', 'POST'])
def setup_proxy():
    """Show form and handle proxy setup"""
    if request.method == 'GET':
        return render_template('index.html')
    return handle_setup_post()


def create_cors_preflight_response():
    """Create CORS preflight response"""
    resp = Response('', status=200)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    return resp


def build_target_url(base_url: str, path: str) -> str:
    """Build target URL from base and path"""
    if path:
        base = base_url if base_url.endswith('/') else base_url + '/'
        target = urljoin(base, path)
    else:
        target = base_url
    if request.query_string:
        target += f"?{request.query_string.decode()}"
    return target


def add_cors_headers(resp):
    """Add CORS headers to response"""
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


def build_redirect_path(parsed_loc) -> str:
    """Build redirect path from parsed location"""
    path = parsed_loc.path or '/'
    return f"{path}?{parsed_loc.query}" if parsed_loc.query else path


def rewrite_redirect_location(location: str, domains: list) -> str:
    """Rewrite redirect location header"""
    parsed_loc = urlparse(location)
    if parsed_loc.netloc in domains or not parsed_loc.netloc:
        return build_redirect_path(parsed_loc)
    return location


def is_redirect(status_code: int) -> bool:
    """Check if status code is redirect"""
    return 300 <= status_code < 400


def handle_redirect_response(resp, upstream_resp, domains: list):
    """Handle redirect responses"""
    if is_redirect(upstream_resp.status_code):
        location = upstream_resp.headers.get('Location')
        if location:
            resp.headers['Location'] = rewrite_redirect_location(location, domains)
    return resp


def process_proxy_request(base_url: str, path: str, domains: list):
    """Process proxy request and return response"""
    target_url = build_target_url(base_url, path)
    if not is_safe_url(target_url):
        return "Blocked internal address", 403
    upstream_resp = forward_request(target_url, request.method)
    resp = create_response(upstream_resp, base_url, domains)
    resp = add_cors_headers(resp)
    return handle_redirect_response(resp, upstream_resp, domains)


def handle_proxy_error(e: requests.RequestException):
    """Handle proxy request error"""
    logger.exception("Upstream request failed")
    return f"Upstream error: {e}", 502


def handle_non_options_request(path):
    """Handle non-OPTIONS proxy requests"""
    base_url, domains = get_cookies()
    if not base_url:
        return redirect('/maxme')
    try:
        return process_proxy_request(base_url, path, domains)
    except requests.RequestException as e:
        return handle_proxy_error(e)


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def proxy_request(path):
    """Handle all requests and proxy to target"""
    if request.method == 'OPTIONS':
        return create_cors_preflight_response()
    return handle_non_options_request(path)


@app.route('/health')
def health():
    """Health check"""
    return {"status": "ok"}


# ------------------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
