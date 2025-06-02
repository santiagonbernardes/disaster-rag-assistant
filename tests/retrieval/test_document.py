import tempfile
from pathlib import Path
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
        content = doc.markdown()

        # Verify download happened
        mock_get.assert_called_once_with(url)
        
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
    def test_load_from_cache(
        self, mock_get, mock_openai, mock_llama_parse, temp_cache
    ):
        """Test loading document from cache without download."""
        url = "https://example.com/cached.pdf"
        
        # Pre-populate cache
        temp_cache.save_original(url, b"Cached content")
        temp_cache.save_metadata(url, {"content_type": "application/pdf"})

        # Create document with cache
        doc = Document(url, mock_openai, mock_llama_parse, cache=temp_cache)

        # Access should use cache
        content = doc.markdown()

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