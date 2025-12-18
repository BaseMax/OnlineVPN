#!/usr/bin/env python3
"""
Test script for URL replacement functionality
"""

from app import replace_urls_in_content
from config import MIRROR_DOMAIN

def test_url_replacement():
    """Test the URL replacement logic with various scenarios"""
    
    # Test case 1: Basic YouTube URL replacement
    print("Test 1: Basic YouTube URL replacement")
    content = """
    <a href="https://youtube.com/watch?v=abc123">Watch Video</a>
    <a href="http://youtube.com/watch?v=xyz789">Another Video</a>
    <a href="https://www.youtube.com/watch?v=def456">Third Video</a>
    <a href="http://www.youtube.com/watch?v=ghi012">Fourth Video</a>
    """
    domains = ["youtube.com", "www.youtube.com"]
    result = replace_urls_in_content(content, domains, "text/html")
    print("Original:", content[:100])
    print("Result:", result[:200])
    assert f"https://{MIRROR_DOMAIN}/watch?v=abc123" in result
    assert f"https://{MIRROR_DOMAIN}/watch?v=xyz789" in result
    assert f"https://{MIRROR_DOMAIN}/watch?v=def456" in result
    assert f"https://{MIRROR_DOMAIN}/watch?v=ghi012" in result
    print("✓ Test 1 passed\n")
    
    # Test case 2: URLs in JavaScript
    print("Test 2: URLs in JavaScript")
    content = """
    var url = "https://youtube.com/api/video";
    fetch("http://youtube.com/data");
    """
    domains = ["youtube.com"]
    result = replace_urls_in_content(content, domains, "application/javascript")
    print("Result:", result)
    assert f"https://{MIRROR_DOMAIN}/api/video" in result
    assert f"https://{MIRROR_DOMAIN}/data" in result
    print("✓ Test 2 passed\n")
    
    # Test case 3: Multiple domains
    print("Test 3: Multiple domains")
    content = """
    <a href="https://google.com/search">Google</a>
    <a href="https://youtube.com/watch">YouTube</a>
    <a href="https://facebook.com/page">Facebook</a>
    """
    domains = ["google.com", "youtube.com", "facebook.com"]
    result = replace_urls_in_content(content, domains, "text/html")
    print("Result:", result)
    assert f"https://{MIRROR_DOMAIN}/search" in result
    assert f"https://{MIRROR_DOMAIN}/watch" in result
    assert f"https://{MIRROR_DOMAIN}/page" in result
    print("✓ Test 3 passed\n")
    
    # Test case 4: URLs with complex paths
    print("Test 4: URLs with complex paths")
    content = """
    <a href="https://youtube.com/watch?v=abc&t=10s&list=xyz">Video</a>
    <img src="http://youtube.com/img/thumbnail/abc.jpg">
    """
    domains = ["youtube.com"]
    result = replace_urls_in_content(content, domains, "text/html")
    print("Result:", result)
    assert f"https://{MIRROR_DOMAIN}/watch?v=abc&t=10s&list=xyz" in result
    assert f"https://{MIRROR_DOMAIN}/img/thumbnail/abc.jpg" in result
    print("✓ Test 4 passed\n")
    
    # Test case 5: URLs without path
    print("Test 5: URLs without path")
    content = """
    <a href="https://youtube.com">Home</a>
    <a href="https://youtube.com/">Home with slash</a>
    """
    domains = ["youtube.com"]
    result = replace_urls_in_content(content, domains, "text/html")
    print("Result:", result)
    # Should handle URLs without paths
    assert MIRROR_DOMAIN in result
    print("✓ Test 5 passed\n")
    
    # Test case 6: Don't replace non-matching domains
    print("Test 6: Don't replace non-matching domains")
    content = """
    <a href="https://google.com/search">Should not change</a>
    <a href="https://youtube.com/watch">Should change</a>
    """
    domains = ["youtube.com"]
    result = replace_urls_in_content(content, domains, "text/html")
    print("Result:", result)
    assert "https://google.com/search" in result  # Should remain unchanged
    assert f"https://{MIRROR_DOMAIN}/watch" in result
    print("✓ Test 6 passed\n")
    
    # Test case 7: Handle relative URLs with base_url
    print("Test 7: Handle relative URLs with base_url")
    content = """
    <a href="/watch?v=abc123">Watch Video</a>
    <img src="/img/thumbnail.jpg">
    <script src="/js/player.js"></script>
    <a href="/api/data">API Link</a>
    """
    domains = ["youtube.com"]
    base_url = "https://youtube.com/home"
    result = replace_urls_in_content(content, domains, "text/html", base_url)
    print("Result:", result)
    assert f'href="https://{MIRROR_DOMAIN}/watch?v=abc123"' in result
    assert f'src="https://{MIRROR_DOMAIN}/img/thumbnail.jpg"' in result
    assert f'src="https://{MIRROR_DOMAIN}/js/player.js"' in result
    assert f'href="https://{MIRROR_DOMAIN}/api/data"' in result
    print("✓ Test 7 passed\n")
    
    # Test case 8: Don't replace protocol-relative URLs as relative paths
    print("Test 8: Protocol-relative URLs should be handled correctly")
    content = """
    <a href="//youtube.com/watch">Protocol-relative</a>
    <a href="/watch">Relative path</a>
    """
    domains = ["youtube.com"]
    base_url = "https://youtube.com"
    result = replace_urls_in_content(content, domains, "text/html", base_url)
    print("Result:", result)
    # Protocol-relative should be replaced
    assert f'href="https://{MIRROR_DOMAIN}/watch"' in result
    # Count should be 2 (both should be replaced)
    assert result.count(f'{MIRROR_DOMAIN}/watch') == 2
    print("✓ Test 8 passed\n")
    
    # Test case 9: Don't replace relative URLs if base domain doesn't match
    print("Test 9: Don't replace relative URLs for non-matching base domain")
    content = """
    <a href="/watch?v=123">Watch</a>
    <img src="/img/pic.jpg">
    """
    domains = ["youtube.com"]
    base_url = "https://google.com/search"  # Different domain
    result = replace_urls_in_content(content, domains, "text/html", base_url)
    print("Result:", result)
    # Should NOT be replaced since base domain (google.com) is not in domains list
    assert 'href="/watch?v=123"' in result
    assert 'src="/img/pic.jpg"' in result
    print("✓ Test 9 passed\n")
    
    # Test case 10: Handle mixed absolute and relative URLs
    print("Test 10: Mixed absolute and relative URLs")
    content = """
    <a href="https://youtube.com/watch?v=abc">Absolute</a>
    <a href="/watch?v=def">Relative</a>
    <img src="https://youtube.com/img/thumb1.jpg">
    <img src="/img/thumb2.jpg">
    """
    domains = ["youtube.com"]
    base_url = "https://youtube.com"
    result = replace_urls_in_content(content, domains, "text/html", base_url)
    print("Result:", result)
    # All should be replaced
    assert result.count(MIRROR_DOMAIN) == 4
    assert f'href="https://{MIRROR_DOMAIN}/watch?v=abc"' in result
    assert f'href="https://{MIRROR_DOMAIN}/watch?v=def"' in result
    assert f'src="https://{MIRROR_DOMAIN}/img/thumb1.jpg"' in result
    assert f'src="https://{MIRROR_DOMAIN}/img/thumb2.jpg"' in result
    print("✓ Test 10 passed\n")
    
    print("=" * 50)
    print("All tests passed successfully! ✓")
    print("=" * 50)

if __name__ == "__main__":
    test_url_replacement()
