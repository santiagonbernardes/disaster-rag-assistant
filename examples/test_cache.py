#!/usr/bin/env python3
"""Example demonstrating DocumentCache usage."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.repositories.document_cache import DocumentCache


def main():
    # Initialize cache
    cache = DocumentCache()

    # Example URL
    url = "https://example.com/emergency-guide.pdf"

    # Check if document is cached
    print(f"Document cached: {cache.exists(url)}")

    # Simulate downloading a document
    if not cache.has_original(url):
        print("Downloading document...")
        content = b"This is a sample emergency guide content..."
        cache.save_original(url, content)
        print("Document saved to cache!")
    else:
        print("Document already in cache!")

    # Load from cache
    cached_content = cache.load_original(url)
    print(f"Loaded {len(cached_content)} bytes from cache")

    # Check metadata
    metadata = cache.load_metadata(url)
    print(f"Metadata: {metadata}")

    # Cache statistics
    stats = cache.get_cache_size()
    print(f"Cache stats: {stats}")

    # List all cached documents
    docs = cache.list_cached_documents()
    print(f"Total cached documents: {len(docs)}")


if __name__ == "__main__":
    main()
