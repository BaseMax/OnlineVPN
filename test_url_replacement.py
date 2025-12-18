#!/usr/bin/env python3
"""
Test script for URL replacement functionality
"""

from app import replace_urls_in_content

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
    assert "https://mirror.proxy.maxbase.ir/watch?v=abc123" in result
    assert "https://mirror.proxy.maxbase.ir/watch?v=xyz789" in result
    assert "https://mirror.proxy.maxbase.ir/watch?v=def456" in result
    assert "https://mirror.proxy.maxbase.ir/watch?v=ghi012" in result
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
    assert "https://mirror.proxy.maxbase.ir/api/video" in result
    assert "https://mirror.proxy.maxbase.ir/data" in result
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
    assert "https://mirror.proxy.maxbase.ir/search" in result
    assert "https://mirror.proxy.maxbase.ir/watch" in result
    assert "https://mirror.proxy.maxbase.ir/page" in result
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
    assert "https://mirror.proxy.maxbase.ir/watch?v=abc&t=10s&list=xyz" in result
    assert "https://mirror.proxy.maxbase.ir/img/thumbnail/abc.jpg" in result
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
    assert "mirror.proxy.maxbase.ir" in result
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
    assert "https://mirror.proxy.maxbase.ir/watch" in result
    print("✓ Test 6 passed\n")
    
    print("=" * 50)
    print("All tests passed successfully! ✓")
    print("=" * 50)

if __name__ == "__main__":
    test_url_replacement()
