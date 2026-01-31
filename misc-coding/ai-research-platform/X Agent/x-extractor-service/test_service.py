#!/usr/bin/env python3
"""Test script for X Post Content Extraction Service."""

import asyncio
import json
import time
from app.extractor import XPostExtractor
from app.models import ExtractRequest


async def test_extractor():
    """Test the core extractor functionality."""
    print("Testing X Post Content Extractor...")
    
    # Test URLs
    test_urls = [
        "https://x.com/elonmusk/status/1812258574049157405",
        "https://x.com/test/status/123456789"
    ]
    
    async with XPostExtractor() as extractor:
        print(f"Testing with URLs: {test_urls}")
        
        start_time = time.time()
        posts = await extractor.extract_multiple_posts(test_urls)
        end_time = time.time()
        
        print(f"Extraction completed in {end_time - start_time:.2f} seconds")
        print(f"Successfully extracted {len(posts)} posts")
        
        for i, post in enumerate(posts):
            if post:
                print(f"\nPost {i+1}:")
                print(f"  URL: {post.post_url}")
                print(f"  ID: {post.post_id}")
                print(f"  Author: {post.author.display_name} (@{post.author.username})")
                print(f"  Content: {post.content[:100]}..." if post.content else "  Content: (empty)")
                print(f"  Engagement: {post.engagement.likes} likes, {post.engagement.retweets} retweets")
            else:
                print(f"\nPost {i+1}: Failed to extract")


def test_request_validation():
    """Test request validation."""
    print("\nTesting request validation...")
    
    # Valid request
    try:
        valid_request = ExtractRequest(urls=["https://x.com/test/status/123"])
        print("✓ Valid request passed validation")
    except Exception as e:
        print(f"✗ Valid request failed: {e}")
    
    # Invalid request - empty URLs
    try:
        invalid_request = ExtractRequest(urls=[])
        print("✗ Empty URLs should have failed validation")
    except Exception as e:
        print("✓ Empty URLs correctly failed validation")


if __name__ == "__main__":
    print("X Post Content Extraction Service - Test Suite")
    print("=" * 50)
    
    # Test request validation
    test_request_validation()
    
    # Test extractor
    asyncio.run(test_extractor())
    
    print("\nTest suite completed!")

