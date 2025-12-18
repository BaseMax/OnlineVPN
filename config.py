"""
Configuration file for OnlineVPN
"""

import os


CORS_ALLOW_ORIGINS = "*"
CORS_ALLOW_METHODS = (
    "GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD"
)
CORS_ALLOW_HEADERS = (
    "Accept, "
    "Accept-Encoding, "
    "Accept-Language, "
    "Authorization, "
    "Cache-Control, "
    "Connection, "
    "Content-Length, "
    "Content-Range, "
    "Content-Type, "
    "DNT, "
    "If-Modified-Since, "
    "If-None-Match, "
    "Origin, "
    "Pragma, "
    "Range, "
    "Referer, "
    "User-Agent, "
    "X-Requested-With"
)
CORS_EXPOSE_HEADERS = (
    "Accept-Ranges, "
    "Age, "
    "Cache-Control, "
    "Content-Disposition, "
    "Content-Encoding, "
    "Content-Length, "
    "Content-Range, "
    "Date, "
    "ETag, "
    "Expires, "
    "Last-Modified, "
    "Location, "
    "Server, "
    "Transfer-Encoding, "
    "Vary"
)

# Single domain configuration for unified proxy service
PROXY_DOMAIN = "proxy.maxbase.ir"

# Prefix for proxied domain routes (e.g., '/_/')
PROXY_ROUTE_PREFIX = "/_/"

# Request timeout in seconds
REQUEST_TIMEOUT = 30

# User agent for requests
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

# Content types that should be processed for URL replacement
PROCESSABLE_CONTENT_TYPES = [
    'text/',
    'application/javascript',
    'application/json',
    'application/xml'
]

# SSL verification settings
# Set to False to disable SSL certificate verification
# This allows proxying sites with SSL issues or self-signed certificates
# WARNING: Disabling SSL verification can expose you to man-in-the-middle attacks
# Can be overridden with SSL_VERIFY environment variable (set to 'true' to enable)
SSL_VERIFY = os.environ.get('SSL_VERIFY', 'false').lower() == 'true'
