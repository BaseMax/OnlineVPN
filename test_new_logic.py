#!/usr/bin/env python3
"""
Test script for new proxy logic
"""

from app import (
    get_base_url,
    get_path_from_url,
    replace_absolute_urls,
    replace_protocol_relative,
    replace_relative_urls,
    rewrite_content
)

def test_get_base_url():
    """Test base URL extraction"""
    print("Test 1: Extract base URL")
    
    test_cases = [
        ("https://example.com/category/post1/", "https://example.com"),
        ("https://test.domain.com/category/post1/", "https://test.domain.com"),
        ("http://api.example.com/v1/users", "http://api.example.com"),
        ("https://example.com/", "https://example.com"),
    ]
    
    for url, expected in test_cases:
        result = get_base_url(url)
        status = "✓" if result == expected else "✗"
        print(f"{status} {url} -> {result} (expected {expected})")
        assert result == expected, f"Expected {expected}, got {result}"
    
    print("✓ Test 1 passed\n")


def test_get_path_from_url():
    """Test path extraction"""
    print("Test 2: Extract path from URL")
    
    test_cases = [
        ("https://example.com/category/post1/", "/category/post1/"),
        ("https://example.com/", "/"),
        ("https://example.com", "/"),
        ("https://example.com/page?query=value", "/page?query=value"),
    ]
    
    for url, expected in test_cases:
        result = get_path_from_url(url)
        status = "✓" if result == expected else "✗"
        print(f"{status} {url} -> {result} (expected {expected})")
        assert result == expected, f"Expected {expected}, got {result}"
    
    print("✓ Test 2 passed\n")


def test_replace_absolute_urls():
    """Test absolute URL replacement"""
    print("Test 3: Replace absolute URLs")
    
    content = '''
    <a href="https://example.com/page1">Link 1</a>
    <a href="https://cdn.example.com/file.js">CDN</a>
    <a href="https://other.com/page">Other</a>
    '''
    
    domains = ["example.com", "cdn.example.com"]
    proxy_base = "https://proxy.maxbase.ir"
    
    result = replace_absolute_urls(content, domains, proxy_base)
    
    print("Result snippet:", result[:200])
    
    # Check that example.com URLs are replaced
    assert "https://proxy.maxbase.ir" in result
    # Check that other.com URLs are NOT replaced
    assert "https://other.com/page" in result
    
    print("✓ Test 3 passed\n")


def test_replace_protocol_relative():
    """Test protocol-relative URL replacement"""
    print("Test 4: Replace protocol-relative URLs (//)")
    
    content = '''
    <script src="//example.com/script.js"></script>
    <img src="//cdn.example.com/image.jpg">
    <link href="//other.com/style.css">
    '''
    
    domains = ["example.com", "cdn.example.com"]
    proxy_base = "https://proxy.maxbase.ir"
    
    result = replace_protocol_relative(content, domains, proxy_base)
    
    print("Result snippet:", result[:300])
    
    # Check that example.com URLs are replaced
    assert "//proxy.maxbase.ir" in result
    # Check that other.com URLs are NOT replaced
    assert "//other.com/style.css" in result
    
    print("✓ Test 4 passed\n")


def test_replace_relative_urls():
    """Test relative URL replacement"""
    print("Test 5: Replace relative URLs (/, ./)")
    
    content = '''
    <a href="/about">About</a>
    <img src="/images/logo.png">
    <script src="./js/app.js"></script>
    <link href="./css/style.css">
    '''
    
    base_url = "https://example.com"
    proxy_base = "https://proxy.maxbase.ir"
    
    result = replace_relative_urls(content, base_url, proxy_base)
    
    print("Result snippet:", result[:400])
    
    # Check that relative URLs are replaced with proxy base
    assert 'href="https://proxy.maxbase.ir/about"' in result
    assert 'src="https://proxy.maxbase.ir/images/logo.png"' in result
    assert 'src="https://proxy.maxbase.ir/js/app.js"' in result
    
    print("✓ Test 5 passed\n")


def test_rewrite_content():
    """Test complete content rewriting"""
    print("Test 6: Complete content rewriting")
    
    content = '''
    <html>
        <head>
            <script src="https://example.com/script.js"></script>
            <link rel="stylesheet" href="//cdn.example.com/style.css">
        </head>
        <body>
            <a href="/page">Link 1</a>
            <a href="./about">Link 2</a>
            <img src="https://example.com/logo.png">
            <a href="https://external.com/page">External</a>
        </body>
    </html>
    '''
    
    base_url = "https://example.com"
    domains = ["example.com", "cdn.example.com"]
    
    result = rewrite_content(content, base_url, domains)
    
    print("Result snippet:", result[:500])
    
    # Check that proxy base is present
    assert "proxy.maxbase.ir" in result
    # Check that external URLs are preserved
    assert "https://external.com/page" in result
    
    print("✓ Test 6 passed\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing New Proxy Logic")
    print("=" * 60)
    print()
    
    try:
        test_get_base_url()
        test_get_path_from_url()
        test_replace_absolute_urls()
        test_replace_protocol_relative()
        test_replace_relative_urls()
        test_rewrite_content()
        
        print("=" * 60)
        print("All tests passed successfully! ✓")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
