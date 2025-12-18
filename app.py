from flask import Flask, request, render_template, Response
import requests
from urllib.parse import urljoin, urlparse
import re

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
    
    try:
        # Fetch the content from the target URL
        response = requests.get(target_url, timeout=30)
        content = response.text
        
        # Replace domains in the content
        for domain in domains_to_replace:
            if domain:
                # Replace domain references in the content
                content = content.replace(f'http://{domain}', f'/proxy?url=http://{domain}')
                content = content.replace(f'https://{domain}', f'/proxy?url=https://{domain}')
        
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
