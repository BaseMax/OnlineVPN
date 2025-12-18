import socket
import ipaddress
import re
import logging
from urllib.parse import urlparse, urljoin

import requests
import urllib3
from flask import Flask, request, Response, redirect, make_response, render_template

from config import (
    PROXY_DOMAIN,
    SSL_VERIFY,
    REQUEST_TIMEOUT,
    PROCESSABLE_CONTENT_TYPES,
    PROXY_ROUTE_PREFIX,
)

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ------------------------------------------------------------------------------
# Flask
# ------------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = "change-me"

# ------------------------------------------------------------------------------
# SSRF protection
# ------------------------------------------------------------------------------
BLOCKED_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def resolve_ip(hostname: str) -> str | None:
    try:
        return socket.gethostbyname(hostname)
    except Exception:
        return None


def is_blocked_ip(ip: str) -> bool:
    ip_obj = ipaddress.ip_address(ip)
    return any(ip_obj in net for net in BLOCKED_IP_RANGES)


def is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    if not parsed.hostname:
        return False
    ip = resolve_ip(parsed.hostname)
    return ip is not None and not is_blocked_ip(ip)

# ------------------------------------------------------------------------------
# Proxy URL helpers
# ------------------------------------------------------------------------------
def proxy_root() -> str:
    return f"https://{PROXY_DOMAIN}"


def proxy_for_domain(domain: str) -> str:
    return f"{proxy_root()}{PROXY_ROUTE_PREFIX}{domain}"


def is_main_domain(domain: str, base_url: str) -> bool:
    return domain.lower() == urlparse(base_url).netloc.lower()


# ------------------------------------------------------------------------------
# Content rewriting (CORRECT LOGIC)
# ------------------------------------------------------------------------------
def rewrite_absolute_urls(content: str, domain: str, base_url: str) -> str:
    escaped = re.escape(domain)

    pattern = rf"https?://{escaped}([^\s\"\'<>]*)"

    def repl(match):
        path = match.group(1) or ""
        if is_main_domain(domain, base_url):
            return f"{proxy_root()}{path}"
        return f"{proxy_for_domain(domain)}{path}"

    return re.sub(pattern, repl, content)


def rewrite_protocol_relative_urls(content: str, domain: str, base_url: str) -> str:
    escaped = re.escape(domain)
    pattern = rf"//{escaped}([^\s\"\'<>]*)"

    def repl(match):
        path = match.group(1) or ""
        if is_main_domain(domain, base_url):
            return f"//{PROXY_DOMAIN}{path}"
        return f"{proxy_for_domain(domain)}{path}"

    return re.sub(pattern, repl, content)


def rewrite_content(content: str, domains: list[str], base_url: str) -> str:
    for domain in domains:
        content = rewrite_absolute_urls(content, domain, base_url)
        content = rewrite_protocol_relative_urls(content, domain, base_url)
    return content


# ------------------------------------------------------------------------------
# HTTP proxy core
# ------------------------------------------------------------------------------
def forward_request(target_url: str):
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in ("host", "content-length")
    }
    headers['Accept-Encoding'] = 'identity'
    
    return requests.request(
        method=request.method,
        url=target_url,
        headers=headers,
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False,
        timeout=REQUEST_TIMEOUT,
        verify=SSL_VERIFY,
    )


def build_target_url(base_url: str, path: str) -> str:
    base = base_url.rstrip("/") + "/"
    target = urljoin(base, path)
    if request.query_string:
        target += "?" + request.query_string.decode()
    return target


def create_proxy_response(upstream, base_url: str, domains: list[str]):
    content = upstream.content
    content_type = upstream.headers.get("Content-Type", "")

    if any(ct in content_type for ct in PROCESSABLE_CONTENT_TYPES):
        try:
            decoded = content.decode("utf-8", errors="ignore")
            decoded = rewrite_content(decoded, domains, base_url)
            content = decoded.encode("utf-8")
        except Exception:
            pass

    resp = Response(content, status=upstream.status_code)

    for k, v in upstream.headers.items():
        if k.lower() not in ("content-length", "content-encoding"):
            resp.headers[k] = v

    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------
@app.route("/maxme", methods=["GET", "POST"])
def setup():
    if request.method == "GET":
        return render_template("index.html")

    target_url = request.form.get("target_url", "").strip()
    if not target_url:
        return "Missing target_url", 400

    if not is_safe_url(target_url):
        return "Blocked target", 403

    parsed = urlparse(target_url)
    domains = request.form.get("domains", "").split(",")
    domains = [d.strip() for d in domains if d.strip()] or [parsed.netloc]

    resp = make_response(redirect("/"))
    resp.set_cookie("base_url", f"{parsed.scheme}://{parsed.netloc}")
    resp.set_cookie("domains", ",".join(domains))
    return resp


def get_proxy_context():
    base_url = request.cookies.get("base_url")
    domains = request.cookies.get("domains", "").split(",")
    return base_url, [d for d in domains if d]


@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def proxy(path):
    base_url, domains = get_proxy_context()
    if not base_url:
        return redirect("/maxme")

    if path.startswith(PROXY_ROUTE_PREFIX.lstrip("/")):
        _, domain, rest = path.split("/", 2)
        if domain not in domains:
            return "Forbidden domain", 403
        base_url = f"https://{domain}"
        path = rest

    target_url = build_target_url(base_url, path)

    if not is_safe_url(target_url):
        return "Blocked target", 403

    upstream = forward_request(target_url)
    return create_proxy_response(upstream, base_url, domains)


@app.route("/health")
def health():
    return {"status": "ok"}
