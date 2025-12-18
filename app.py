import socket
import ipaddress
import re
import logging
from urllib.parse import urlparse, urljoin, quote
from flask import Flask, request, render_template, Response, session
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
    try:
        parsed = urlparse(url)
        if not parsed.hostname:
            return False

        ip = ipaddress.ip_address(socket.gethostbyname(parsed.hostname))
        return not any(ip in net for net in BLOCKED_IP_RANGES)
    except Exception:
        return False


# ------------------------------------------------------------------------------
# URL helpers
# ------------------------------------------------------------------------------

def build_proxy_url(target_url, allowed_domains):
    url = f"https://{PROXY_DOMAIN}/proxy?url={quote(target_url)}"
    if allowed_domains:
        url += "&domains=" + quote(",".join(allowed_domains))
    return url


def replace_urls_in_content(content, allowed_domains, current_url):
    if not content or not allowed_domains:
        return content

    for domain in allowed_domains:
        escaped = re.escape(domain)

        pattern = rf'(https?://(?:[\w\-]+\.)?{escaped})(/[^\s"\'<>]*)?'

        def repl(match):
            return build_proxy_url(match.group(0), allowed_domains)

        content = re.sub(pattern, repl, content)

    # Relative URLs
    parsed_current = urlparse(current_url)
    if parsed_current.netloc in allowed_domains:
        rel_pattern = r'((?:href|src|action)=["\'])(/(?!/)[^"\'>]+)'

        def rel_repl(m):
            abs_url = urljoin(current_url, m.group(2))
            return m.group(1) + build_proxy_url(abs_url, allowed_domains)

        content = re.sub(rel_pattern, rel_repl, content)

    return content


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/proxy')
def proxy():
    target_url = request.args.get('url')
    domains_param = request.args.get('domains', '')

    if not target_url:
        return "Missing url parameter", 400

    allowed_domains = [d.strip() for d in domains_param.split(',') if d.strip()]

    parsed = urlparse(target_url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return "Invalid URL", 400

    if not is_safe_url(target_url):
        return "Blocked internal address", 403

    if not allowed_domains:
        allowed_domains = [parsed.netloc]

    session['allowed_domains'] = allowed_domains

    # -------------------------------
    # IMPORTANT: force plain content
    # -------------------------------
    headers = {
        'User-Agent': request.headers.get('User-Agent', 'Mozilla/5.0'),
        'Accept': request.headers.get('Accept', '*/*'),
        'Accept-Language': request.headers.get('Accept-Language', 'en-US,en;q=0.9'),
        'Accept-Encoding': 'identity',  # <<< CRITICAL FIX
    }

    try:
        upstream = requests.get(
            target_url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            verify=SSL_VERIFY,
        )

        content_type = upstream.headers.get('Content-Type', '').lower()

        # -----------------------------------
        # TEXT CONTENT → READ + REWRITE
        # -----------------------------------
        if any(ct in content_type for ct in PROCESSABLE_CONTENT_TYPES):
            text = upstream.text
            text = replace_urls_in_content(text, allowed_domains, target_url)

            resp = Response(text, status=upstream.status_code)
            resp.headers['Content-Type'] = content_type
            return resp

        # -----------------------------------
        # BINARY CONTENT → PASS THROUGH
        # -----------------------------------
        resp = Response(
            upstream.content,
            status=upstream.status_code,
            content_type=content_type
        )
        return resp

    except requests.RequestException as e:
        logger.exception("Upstream request failed")
        return f"Upstream error: {e}", 502


@app.route('/health')
def health():
    return {"status": "ok"}, 200


# ------------------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
