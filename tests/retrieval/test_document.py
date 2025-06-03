import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.repositories.document_cache import DocumentCache
from src.retrieval.document import Document


@pytest.fixture
def mock_openai():
    """Mock OpenAI client."""
    return MagicMock()


@pytest.fixture
def mock_llama_parse():
    """Mock LlamaParse client."""
    mock = MagicMock()
    # Setup mock to return pages with markdown content
    mock_page = MagicMock()
    mock_page.md = "# Test Document\n\nThis is test content."
    mock_result = MagicMock()
    mock_result.pages = [mock_page]
    mock.parse.return_value = mock_result
    return mock


@pytest.fixture
def temp_cache():
    """Create temporary cache for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield DocumentCache(cache_dir=tmpdir)


class TestDocumentWithCache:
    @patch("requests.get")
    def test_download_and_cache(
        self, mock_get, mock_openai, mock_llama_parse, temp_cache
    ):
        """Test document download and caching."""
        # Setup mock response
        mock_response = Mock()
        mock_response.content = b"Test PDF content"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.url = "https://example.com/test.pdf"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Create document with cache
        url = "https://example.com/test.pdf"
        doc = Document(url, mock_openai, mock_llama_parse, cache=temp_cache)

        # First access should download
        assert not temp_cache.has_original(url)
        doc.markdown()

        # Verify download happened with headers
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == url
        assert "headers" in call_args[1]
        assert "timeout" in call_args[1]

        # Verify content was cached
        assert temp_cache.has_original(url)
        cached_content = temp_cache.load_original(url)
        assert cached_content == b"Test PDF content"

        # Verify metadata was saved
        metadata = temp_cache.load_metadata(url)
        assert metadata["content_type"] == "application/pdf"
        assert metadata["content_length"] == 16
        assert metadata["status_code"] == 200

    @patch("requests.get")
    def test_load_from_cache(self, mock_get, mock_openai, mock_llama_parse, temp_cache):
        """Test loading document from cache without download."""
        url = "https://example.com/cached.pdf"

        # Pre-populate cache
        temp_cache.save_original(url, b"Cached content")
        temp_cache.save_metadata(url, {"content_type": "application/pdf"})

        # Create document with cache
        doc = Document(url, mock_openai, mock_llama_parse, cache=temp_cache)

        # Access should use cache
        doc.markdown()

        # Verify no download happened
        mock_get.assert_not_called()

        # Verify LlamaParse was called with cached content
        mock_llama_parse.parse.assert_called_once()
        call_args = mock_llama_parse.parse.call_args
        assert call_args[0][0] == b"Cached content"
        assert call_args[1]["extra_info"]["file_name"] == "cached.pdf"

    def test_document_without_cache(self, mock_openai, mock_llama_parse):
        """Test that Document still works without explicit cache."""
        with patch("requests.get") as mock_get:
            # Setup mock response
            mock_response = Mock()
            mock_response.content = b"Test content"
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/plain"}
            mock_response.url = "https://example.com/test.txt"
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Create document without cache (should use default)
            url = "https://example.com/test.txt"
            doc = Document(url, mock_openai, mock_llama_parse)

            # Should still work
            content = doc.markdown()
            assert content == "# Test Document\n\nThis is test content."

    def test_filename_extraction(self, mock_openai, mock_llama_parse, temp_cache):
        """Test filename extraction from URL."""
        # Test various URL patterns
        test_cases = [
            ("https://example.com/document.pdf", "document.pdf"),
            ("https://example.com/path/to/file.docx", "file.docx"),
            ("https://example.com/no-extension", "document"),
            ("https://example.com/", "document"),
        ]

        for url, expected_filename in test_cases:
            doc = Document(url, mock_openai, mock_llama_parse, cache=temp_cache)
            assert doc._get_file_name_from_url(url) == expected_filename

    @patch("requests.get")
    def test_parsed_cache_hit(
        self, mock_get, mock_openai, mock_llama_parse, temp_cache
    ):
        """Test that parsed cache prevents both download and LlamaParse calls."""
        url = "https://example.com/cached.pdf"
        parsed_content = "# Cached Document\n\nThis is cached parsed content."

        # Pre-populate cache with parsed content
        temp_cache.save_parsed(url, parsed_content)

        # Create document with cache
        doc = Document(url, mock_openai, mock_llama_parse, cache=temp_cache)

        # Access should use parsed cache
        content = doc.markdown()

        # Verify no download happened
        mock_get.assert_not_called()

        # Verify no LlamaParse call happened
        mock_llama_parse.parse.assert_not_called()

        # Verify correct content returned
        assert content == parsed_content

    @patch("requests.get")
    def test_cache_progression_original_to_parsed(
        self, mock_get, mock_openai, mock_llama_parse, temp_cache
    ):
        """Test progression from original cache to parsed cache."""
        url = "https://example.com/test.pdf"

        # Pre-populate cache with original only
        temp_cache.save_original(url, b"Original PDF content")

        # Create document with cache
        doc = Document(url, mock_openai, mock_llama_parse, cache=temp_cache)

        # First access should parse but not download
        doc.markdown()

        # Verify no download happened
        mock_get.assert_not_called()

        # Verify LlamaParse was called
        mock_llama_parse.parse.assert_called_once()

        # Verify parsed content was saved to cache
        assert temp_cache.has_parsed(url)
        cached_parsed = temp_cache.load_parsed(url)
        assert cached_parsed == "# Test Document\n\nThis is test content."

    @patch("requests.get")
    def test_document_chunking(
        self, mock_get, mock_openai, mock_llama_parse, temp_cache
    ):
        """Test document chunking functionality."""
        # Setup mock response
        mock_response = Mock()
        mock_response.content = b"Test PDF content"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.url = "https://example.com/test.pdf"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Create longer content for chunking
        long_content = "This is a test document. " * 100  # Repeat to make it long
        mock_page = MagicMock()
        mock_page.md = long_content
        mock_result = MagicMock()
        mock_result.pages = [mock_page]
        mock_llama_parse.parse.return_value = mock_result

        url = "https://example.com/test.pdf"
        doc = Document(url, mock_openai, mock_llama_parse, cache=temp_cache)

        # Access chunks
        chunks = doc.chunks()

        # Verify chunks were generated
        assert len(chunks) > 0
        assert all(hasattr(chunk, "content") for chunk in chunks)
        assert all(hasattr(chunk, "metadata") for chunk in chunks)

        # Verify chunks were saved to cache
        assert temp_cache.has_chunks(url)
        cached_chunks = temp_cache.load_chunks(url)
        assert len(cached_chunks) == len(chunks)

        # Verify chunk metadata contains URL reference
        for chunk in chunks:
            assert chunk.metadata["url"] == url
            assert "url_hash" in chunk.metadata
            assert "chunked_at" in chunk.metadata

    @patch("requests.get")
    def test_chunks_cache_hit(
        self, mock_get, mock_openai, mock_llama_parse, temp_cache
    ):
        """Test loading chunks from cache."""
        from src.services.document_chunker import Chunk

        url = "https://example.com/test.pdf"
        parsed_content = "# Cached Document\n\nThis is cached content."

        # Pre-populate cache with parsed content and chunks
        temp_cache.save_parsed(url, parsed_content)
        test_chunks = [
            Chunk(
                content="Test chunk",
                index=0,
                start_char=0,
                end_char=10,
                metadata={"url": url},
            )
        ]
        temp_cache.save_chunks(url, test_chunks)

        # Create document with cache
        doc = Document(url, mock_openai, mock_llama_parse, cache=temp_cache)

        # Access chunks
        chunks = doc.chunks()

        # Verify no download or parsing happened
        mock_get.assert_not_called()
        mock_llama_parse.parse.assert_not_called()

        # Verify correct chunks returned
        assert len(chunks) == 1
        assert chunks[0].content == "Test chunk"
