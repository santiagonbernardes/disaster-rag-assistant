import json
import tempfile
from pathlib import Path

import pytest

from src.repositories.document_cache import DocumentCache


@pytest.fixture
def temp_cache_dir():
    """Create a temporary directory for cache testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def document_cache(temp_cache_dir):
    """Create a DocumentCache instance with temporary directory."""
    return DocumentCache(cache_dir=temp_cache_dir)


class TestDocumentCache:
    def test_init_creates_directory(self, temp_cache_dir):
        """Test that initialization creates the cache directory."""
        cache_dir = temp_cache_dir / "test_cache"
        assert not cache_dir.exists()

        DocumentCache(cache_dir=cache_dir)
        assert cache_dir.exists()

    def test_get_document_hash(self, document_cache):
        """Test URL hash generation."""
        url1 = "https://example.com/doc1"
        url2 = "https://example.com/doc2"

        hash1 = document_cache.get_document_hash(url1)
        hash2 = document_cache.get_document_hash(url2)

        # Hashes should be consistent
        assert hash1 == document_cache.get_document_hash(url1)
        # Different URLs should have different hashes
        assert hash1 != hash2
        # Hash should be 16 characters
        assert len(hash1) == 16

    def test_save_and_load_original(self, document_cache):
        """Test saving and loading original document."""
        url = "https://example.com/test.pdf"
        content = b"Test PDF content"

        # Initially, document should not exist
        assert not document_cache.exists(url)
        assert not document_cache.has_original(url)
        assert document_cache.load_original(url) is None

        # Save original
        document_cache.save_original(url, content)

        # Now it should exist
        assert document_cache.exists(url)
        assert document_cache.has_original(url)

        # Load and verify content
        loaded_content = document_cache.load_original(url)
        assert loaded_content == content

    def test_metadata_operations(self, document_cache):
        """Test metadata save and load operations."""
        url = "https://example.com/test.pdf"
        metadata = {"title": "Test Document", "size": 1024}

        # Initially no metadata
        assert document_cache.load_metadata(url) is None

        # Save metadata
        document_cache.save_metadata(url, metadata)

        # Load and verify
        loaded_metadata = document_cache.load_metadata(url)
        assert loaded_metadata["title"] == metadata["title"]
        assert loaded_metadata["size"] == metadata["size"]
        assert loaded_metadata["url"] == url
        assert "hash" in loaded_metadata
        assert "updated_at" in loaded_metadata

    def test_update_metadata(self, document_cache):
        """Test metadata update functionality."""
        url = "https://example.com/test.pdf"
        content = b"Test content"

        # Save original (which creates metadata)
        document_cache.save_original(url, content)

        # Load metadata
        metadata = document_cache.load_metadata(url)
        assert "original_saved" in metadata

        # Update metadata
        document_cache._update_metadata(url, {"processed": True})

        # Verify update
        updated_metadata = document_cache.load_metadata(url)
        assert updated_metadata["processed"] is True
        assert "original_saved" in updated_metadata  # Original field preserved

    def test_list_cached_documents(self, document_cache):
        """Test listing all cached documents."""
        urls = [
            "https://example.com/doc1.pdf",
            "https://example.com/doc2.pdf",
            "https://example.com/doc3.pdf",
        ]

        # Cache multiple documents
        for i, url in enumerate(urls):
            document_cache.save_original(url, f"Content {i}".encode())

        # List cached documents
        cached_docs = document_cache.list_cached_documents()
        assert len(cached_docs) == 3

        # Verify URLs are in the list
        cached_urls = [doc["url"] for doc in cached_docs]
        for url in urls:
            assert url in cached_urls

    def test_clear_cache(self, document_cache):
        """Test clearing cache for a specific URL."""
        url = "https://example.com/test.pdf"
        content = b"Test content"

        # Save document
        document_cache.save_original(url, content)
        assert document_cache.exists(url)

        # Clear cache
        document_cache.clear_cache(url)
        assert not document_cache.exists(url)
        assert document_cache.load_original(url) is None

    def test_get_cache_size(self, document_cache):
        """Test cache size calculation."""
        # Initially empty
        stats = document_cache.get_cache_size()
        assert stats["document_count"] == 0
        assert stats["total_size_bytes"] == 0

        # Add documents
        document_cache.save_original("https://example.com/doc1", b"A" * 1000)
        document_cache.save_original("https://example.com/doc2", b"B" * 2000)

        # Check size
        stats = document_cache.get_cache_size()
        assert stats["document_count"] == 2
        assert stats["total_size_bytes"] > 3000  # At least the content size
        assert "total_size_mb" in stats

    def test_directory_structure(self, document_cache):
        """Test that the correct directory structure is created."""
        url = "https://example.com/test.pdf"
        content = b"Test content"

        document_cache.save_original(url, content)

        # Check directory structure
        doc_path = document_cache.get_document_path(url)
        assert doc_path.exists()
        assert (doc_path / "original.bin").exists()
        assert (doc_path / "metadata.json").exists()

        # Verify metadata content
        metadata_content = json.loads((doc_path / "metadata.json").read_text())
        assert metadata_content["url"] == url

    def test_save_and_load_parsed(self, document_cache):
        """Test saving and loading parsed markdown content."""
        url = "https://example.com/test.pdf"
        markdown_content = "# Test Document\n\nThis is parsed content."

        # Initially, parsed content should not exist
        assert not document_cache.has_parsed(url)
        assert document_cache.load_parsed(url) is None

        # Save parsed content
        document_cache.save_parsed(url, markdown_content)

        # Now it should exist
        assert document_cache.has_parsed(url)

        # Load and verify content
        loaded_content = document_cache.load_parsed(url)
        assert loaded_content == markdown_content

        # Check metadata was updated
        metadata = document_cache.load_metadata(url)
        assert "parsed_saved" in metadata

    def test_cache_progression(self, document_cache):
        """Test the progression of cache states."""
        url = "https://example.com/doc.pdf"

        # Initially nothing cached
        assert not document_cache.exists(url)
        assert not document_cache.has_original(url)
        assert not document_cache.has_parsed(url)

        # Save original
        document_cache.save_original(url, b"Original content")
        assert document_cache.exists(url)
        assert document_cache.has_original(url)
        assert not document_cache.has_parsed(url)

        # Save parsed
        document_cache.save_parsed(url, "Parsed content")
        assert document_cache.has_parsed(url)

        # Both should exist
        assert document_cache.load_original(url) == b"Original content"
        assert document_cache.load_parsed(url) == "Parsed content"

    def test_save_and_load_chunks(self, document_cache):
        """Test saving and loading document chunks."""
        from src.services.document_chunker import Chunk

        url = "https://example.com/test.pdf"
        chunks = [
            Chunk(
                content="First chunk content",
                index=0,
                start_char=0,
                end_char=19,
                metadata={"chunk_index": 0, "total_chunks": 3},
            ),
            Chunk(
                content="Second chunk content",
                index=1,
                start_char=20,
                end_char=40,
                metadata={"chunk_index": 1, "total_chunks": 3},
            ),
            Chunk(
                content="Third chunk content",
                index=2,
                start_char=41,
                end_char=60,
                metadata={"chunk_index": 2, "total_chunks": 3},
            ),
        ]

        # Initially, chunks should not exist
        assert not document_cache.has_chunks(url)
        assert document_cache.load_chunks(url) is None

        # Save chunks
        document_cache.save_chunks(url, chunks)

        # Now chunks should exist
        assert document_cache.has_chunks(url)

        # Load chunks and verify
        loaded_chunks = document_cache.load_chunks(url)
        assert loaded_chunks is not None
        assert len(loaded_chunks) == 3

        # Verify chunk content
        for i, chunk in enumerate(loaded_chunks):
            assert chunk.content == chunks[i].content
            assert chunk.index == chunks[i].index
            assert chunk.start_char == chunks[i].start_char
            assert chunk.end_char == chunks[i].end_char
            assert chunk.metadata == chunks[i].metadata

        # Verify metadata was updated
        metadata = document_cache.load_metadata(url)
        assert metadata["chunk_count"] == 3
        assert "chunks_saved" in metadata

    def test_cache_progression_with_chunks(self, document_cache):
        """Test the full progression of cache states including chunks."""
        from src.services.document_chunker import Chunk

        url = "https://example.com/doc.pdf"

        # Initially nothing cached
        assert not document_cache.exists(url)
        assert not document_cache.has_original(url)
        assert not document_cache.has_parsed(url)
        assert not document_cache.has_chunks(url)

        # Save original
        document_cache.save_original(url, b"Original content")
        assert document_cache.has_original(url)
        assert not document_cache.has_parsed(url)
        assert not document_cache.has_chunks(url)

        # Save parsed
        document_cache.save_parsed(url, "Parsed content")
        assert document_cache.has_parsed(url)
        assert not document_cache.has_chunks(url)

        # Save chunks
        chunks = [
            Chunk(
                content="Test chunk",
                index=0,
                start_char=0,
                end_char=10,
                metadata={"test": True},
            )
        ]
        document_cache.save_chunks(url, chunks)
        assert document_cache.has_chunks(url)

        # All should exist
        assert document_cache.load_original(url) == b"Original content"
        assert document_cache.load_parsed(url) == "Parsed content"
        assert len(document_cache.load_chunks(url)) == 1
