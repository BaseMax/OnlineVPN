#!/usr/bin/env python3
"""
Test script for URL replacement functionality in the new architecture
"""

from app import replace_urls_in_content, build_proxy_url, is_domain_allowed
from config import PROXY_DOMAIN

def test_build_proxy_url():
    """Test proxy URL building"""
    print("Test 1: Build proxy URL")
    
    url = "https://example.com/page"
    domains = ["example.com"]
    result = build_proxy_url(url, domains)
    
    print(f"URL: {url}")
    print(f"Domains: {domains}")
    print(f"Result: {result}")
    
    assert f"https://{PROXY_DOMAIN}/proxy?url=" in result
    assert "example.com" in result
    print("✓ Test 1 passed\n")


def test_is_domain_allowed():
    """Test domain checking"""
    print("Test 2: Check allowed domains")
    
    test_cases = [
        ("https://example.com/page", ["example.com"], True),
        ("https://sub.example.com/page", ["example.com"], True),
        ("https://google.com/page", ["example.com"], False),
        ("https://example.com/page", [], False),
    ]
    
    for url, domains, expected in test_cases:
        result = is_domain_allowed(url, domains)
        status = "✓" if result == expected else "✗"
        print(f"{status} {url} with {domains} -> {result} (expected {expected})")
        assert result == expected
    
    print("✓ Test 2 passed\n")


def test_url_replacement():
    """Test URL replacement in content"""
    print("Test 3: URL replacement in HTML")
    
    content = """
    <html>
        <a href="https://example.com/page1">Link 1</a>
        <a href="https://google.com/search">Link 2</a>
        <img src="https://example.com/image.jpg">
        <script src="/js/app.js"></script>
    </html>
    """
    
    domains = ["example.com"]
    current_url = "https://example.com/index"
    
    result = replace_urls_in_content(content, domains, "text/html", current_url)
    
    print("Original content snippet:")
    print(content[:200])
    print("\nProcessed content snippet:")
    print(result[:400])
    
    # example.com URLs should be replaced
    assert "/proxy?url=" in result
    assert "example.com" in result
    
    # google.com should NOT be replaced (not in allowed domains)
    assert "https://google.com/search" in result
    
    print("✓ Test 3 passed\n")


def test_relative_url_replacement():
    """Test relative URL replacement"""
    print("Test 4: Relative URL replacement")
    
    content = """
    <a href="/about">About</a>
    <img src="/images/logo.png">
    """
    
    domains = ["example.com"]
    current_url = "https://example.com/index"
    
    result = replace_urls_in_content(content, domains, "text/html", current_url)
    
    print("Result:", result[:300])
    
    # Relative URLs should be converted to absolute and proxied
    assert "/proxy?url=" in result
    assert "example.com" in result or "example.com%2F" in result
    
    print("✓ Test 4 passed\n")


def test_no_replacement_for_non_allowed():
    """Test that non-allowed domains are not replaced"""
    print("Test 5: No replacement for non-allowed domains")
    
    content = """
    <a href="https://google.com/search">Google</a>
    <a href="https://facebook.com/page">Facebook</a>
    """
    
    domains = ["example.com"]
    current_url = "https://example.com/index"
    
    result = replace_urls_in_content(content, domains, "text/html", current_url)
    
    print("Result:", result)
    
    # Non-allowed domains should remain unchanged
    assert "https://google.com/search" in result
    assert "https://facebook.com/page" in result
    
    print("✓ Test 5 passed\n")


def test_multiple_domains():
    """Test URL replacement with multiple allowed domains"""
    print("Test 6: Multiple allowed domains")
    
    content = """
    <a href="https://example.com/page">Example</a>
    <img src="https://cdn.example.com/image.jpg">
    <a href="https://google.com/search">Google</a>
    """
    
    domains = ["example.com", "cdn.example.com"]
    current_url = "https://example.com/index"
    
    result = replace_urls_in_content(content, domains, "text/html", current_url)
    
    print("Result snippet:", result[:400])
    
    # Both example.com and cdn.example.com should be proxied
    assert result.count("/proxy?url=") >= 2
    
    # google.com should NOT be proxied
    assert "https://google.com/search" in result
    
    print("✓ Test 6 passed\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing New URL Replacement Architecture")
    print("=" * 60)
    print()
    
    try:
        test_build_proxy_url()
        test_is_domain_allowed()
        test_url_replacement()
        test_relative_url_replacement()
        test_no_replacement_for_non_allowed()
        test_multiple_domains()
        
        print("=" * 60)
        print("All tests passed successfully! ✓")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
