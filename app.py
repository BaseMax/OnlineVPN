from flask import Flask, request, render_template, Response
import requests
from urllib.parse import urlparse

app = Flask(__name__)

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
    
    try:
        # Fetch the content from the target URL with proper headers
        headers = {
            'User-Agent': 'OnlineVPN-Proxy/1.0'
        }
        response = requests.get(target_url, headers=headers, timeout=30, allow_redirects=True)
        content = response.text
        
        # Replace domains in the content (basic implementation)
        # Note: This is a simple string replacement for demonstration
        # A production implementation would need more sophisticated URL rewriting
        for domain in domains_to_replace:
            if domain:
                # Replace domain references in the content
                content = content.replace(f'http://{domain}', f'http://{request.host}')
                content = content.replace(f'https://{domain}', f'http://{request.host}')
        
        return Response(content, mimetype=response.headers.get('content-type', 'text/html'))
    
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
