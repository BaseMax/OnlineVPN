"""
Configuration file for OnlineVPN
"""

# Domain configuration for the two deployment targets
PROXY_DOMAIN = "proxy.maxbase.ir"
MIRROR_DOMAIN = "mirror.proxy.maxbase.ir"

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
import os
SSL_VERIFY = os.environ.get('SSL_VERIFY', 'false').lower() == 'true'
