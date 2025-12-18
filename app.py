#!/usr/bin/env python3
"""
OnlineVPN - Web-based proxy/mirror platform
Main Flask application for proxying and mirroring web content
"""

from flask import Flask, request, render_template_string, Response
import requests
import re
import config

app = Flask(__name__)

# Configuration for the two domains
PROXY_DOMAIN = config.PROXY_DOMAIN
MIRROR_DOMAIN = config.MIRROR_DOMAIN

# HTML template for the home page
HOME_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OnlineVPN - Web Proxy</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        input[type="text"], textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        textarea {
            min-height: 100px;
            resize: vertical;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            width: 100%;
        }
        button:hover {
            background-color: #45a049;
        }
        .help-text {
            font-size: 12px;
            color: #777;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>OnlineVPN - Web Proxy</h1>
        <p style="text-align: center; color: #666;">Access any website through our proxy service</p>
        
        <form method="POST" action="/proxy">
            <div class="form-group">
                <label for="url">Target URL:</label>
                <input type="text" id="url" name="url" placeholder="https://youtube.com/watch" required>
                <div class="help-text">Enter the full URL you want to access</div>
            </div>
            
            <div class="form-group">
                <label for="domains">Domains to Replace (one per line):</label>
                <textarea id="domains" name="domains" placeholder="youtube.com&#10;www.youtube.com" required></textarea>
                <div class="help-text">Enter domains (without http/https) that should be replaced with mirror links</div>
            </div>
            
            <button type="submit">Access via Proxy</button>
        </form>
    </div>
</body>
</html>
"""


def replace_urls_in_content(content, domains_to_replace, content_type):
    """
    Replace URLs in the content with mirror proxy URLs
    
    Args:
        content: The content to process (HTML, CSS, JS, etc.)
        domains_to_replace: List of domains to replace
        content_type: MIME type of the content
        
    Returns:
        Modified content with replaced URLs
    """
    if not domains_to_replace:
        return content
    
    # For binary content, return as-is
    if isinstance(content, bytes) and not content_type.startswith(('text/', 'application/javascript', 'application/json')):
        return content
    
    # Convert bytes to string if needed
    if isinstance(content, bytes):
        try:
            content = content.decode('utf-8')
        except UnicodeDecodeError:
            return content
    
    # Create regex patterns for each domain
    for domain in domains_to_replace:
        domain = domain.strip()
        if not domain:
            continue
        
        # Escape special regex characters in domain
        escaped_domain = re.escape(domain)
        
        # Replace all variations: http://domain, https://domain
        # Pattern matches: (http|https)://domain(/rest/of/url)
        pattern = rf'https?://{escaped_domain}(/[^\s"\'\)]*)?'
        replacement = rf'https://{MIRROR_DOMAIN}\1'
        content = re.sub(pattern, replacement, content)
    
    return content


def fetch_and_process_url(url, domains_to_replace):
    """
    Fetch content from URL and process it to replace domain references
    
    Args:
        url: The URL to fetch
        domains_to_replace: List of domains to replace in the content
        
    Returns:
        Response object with processed content
    """
    try:
        # Fetch the content
        headers = {
            'User-Agent': config.USER_AGENT
        }
        response = requests.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT, allow_redirects=True)
        
        # Get content type
        content_type = response.headers.get('Content-Type', '').lower()
        
        # Process the content
        content = response.content
        
        # Only process text-based content types
        if any(ct in content_type for ct in config.PROCESSABLE_CONTENT_TYPES):
            content = replace_urls_in_content(content, domains_to_replace, content_type)
            if isinstance(content, str):
                content = content.encode('utf-8')
        
        # Return the response
        return Response(
            content,
            status=response.status_code,
            content_type=content_type
        )
        
    except requests.RequestException as e:
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>Error fetching content</h1>
            <p>Failed to fetch content from: {url}</p>
            <p>Error: {str(e)}</p>
            <p><a href="/">Go back</a></p>
        </body>
        </html>
        """
        return Response(error_html, status=500, content_type='text/html')


@app.route('/')
def home():
    """Display the home page with form"""
    return render_template_string(HOME_PAGE_TEMPLATE)


@app.route('/proxy', methods=['POST'])
def proxy():
    """Handle proxy requests from the form"""
    url = request.form.get('url', '').strip()
    domains_input = request.form.get('domains', '').strip()
    
    if not url:
        return "URL is required", 400
    
    # Parse domains list (one per line)
    domains_to_replace = [d.strip() for d in domains_input.split('\n') if d.strip()]
    
    # Fetch and process the URL
    return fetch_and_process_url(url, domains_to_replace)


@app.route('/<path:path>')
def proxy_path(path):
    """
    Handle proxied URLs from mirror domain
    This catches all URLs that come through the mirror and proxies them
    """
    # Reconstruct the original URL
    # The path should be the full path including domain
    # For example: /watch?v=xyz for youtube.com/watch?v=xyz
    
    # Get query string if present
    query_string = request.query_string.decode('utf-8')
    full_path = f"/{path}"
    if query_string:
        full_path += f"?{query_string}"
    
    # Try to determine the original domain from referrer or session
    # For now, we'll return an error asking for proper setup
    error_html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Direct Access Not Supported</title></head>
    <body>
        <h1>Direct Access Not Supported</h1>
        <p>Please use the <a href="/">home page</a> to access websites through the proxy.</p>
        <p>Path requested: {full_path}</p>
    </body>
    </html>
    """
    return Response(error_html, status=400, content_type='text/html')


if __name__ == '__main__':
    # Run the application
    app.run(host='0.0.0.0', port=5000, debug=True)
