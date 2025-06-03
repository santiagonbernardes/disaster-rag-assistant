import pytest
from unittest.mock import Mock, patch
from src.retrieval.document import Document
from src.services.metadata_extractor import LLMMetadataResponse


class TestDocumentIntegration:
    """Test document integration with metadata extraction."""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock OpenAI client."""
        return Mock()

    @pytest.fixture
    def mock_llama_parse(self):
        """Mock LlamaParse service."""
        return Mock()

    @pytest.fixture
    def mock_cache(self):
        """Mock document cache."""
        cache = Mock()
        cache.get_document_hash.return_value = "test_hash"
        return cache

    @pytest.fixture
    def sample_llm_response(self):
        """Sample LLM metadata response."""
        return LLMMetadataResponse(
            document_type="guide",
            information_type="preparation",
            target_audience=["resident"],
            area_type="urban",
            disaster_phase="before"
        )

    def test_document_with_metadata_extraction(
        self, mock_llm_client, mock_llama_parse, mock_cache, sample_llm_response
    ):
        """Test document processing with metadata extraction."""
        # Setup mocks
        mock_cache.load_chunks.return_value = None
        mock_cache.load_parsed.return_value = None
        mock_cache.load_original.return_value = None
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = b"Test document content"
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.status_code = 200
        mock_response.url = "https://example.com/test.pdf"
        
        # Mock LlamaParse response
        mock_page = Mock()
        mock_page.md = "# Test Document\n\nEste é um guia de preparação para enchentes em área urbana."
        mock_parse_result = Mock()
        mock_parse_result.pages = [mock_page]
        mock_llama_parse.parse.return_value = mock_parse_result
        
        # Mock LLM metadata extraction
        mock_llm_response = Mock()
        mock_llm_response.output_parsed = sample_llm_response
        mock_llm_client.responses.create.return_value = mock_llm_response
        
        # Create document instance
        document = Document(
            url="https://example.com/test.pdf",
            client=mock_llm_client,
            llama_parse=mock_llama_parse,
            cache=mock_cache,
        )
        
        # Test document processing with requests mock
        with patch('requests.get', return_value=mock_response):
            chunks = document.chunks()
        
        # Verify chunks were generated with metadata
        assert len(chunks) > 0
        
        # Check that chunks have enriched metadata
        first_chunk = chunks[0]
        assert "url" in first_chunk.metadata
        assert "document_type" in first_chunk.metadata
        assert "information_type" in first_chunk.metadata
        assert "target_audience" in first_chunk.metadata
        assert "disaster_categories" in first_chunk.metadata
        assert "urgency_level" in first_chunk.metadata
        assert "confidence_score" in first_chunk.metadata
        
        # Check chunk-specific metadata
        assert "section_type" in first_chunk.metadata or "has_instructions" in first_chunk.metadata
        
        # Verify LLM was called for metadata extraction
        mock_llm_client.responses.create.assert_called_once()
        
        # Verify cache was called to save chunks
        mock_cache.save_chunks.assert_called_once()

    def test_document_with_cached_chunks_preserves_metadata(
        self, mock_llm_client, mock_llama_parse, mock_cache
    ):
        """Test that cached chunks preserve their metadata."""
        # Setup cached chunks with metadata
        from src.services.document_chunker import Chunk
        cached_chunks = [
            Chunk(
                content="Test chunk content",
                index=0,
                start_char=0,
                end_char=17,
                metadata={
                    "url": "https://example.com/test.pdf",
                    "document_type": "guide",
                    "information_type": "preparation",
                    "target_audience": ["resident"],
                    "has_instructions": True,
                    "section_type": "procedures"
                }
            )
        ]
        
        mock_cache.load_chunks.return_value = cached_chunks
        mock_cache.load_parsed.return_value = "# Test Document\n\nCached content"
        
        # Create document instance
        document = Document(
            url="https://example.com/test.pdf",
            client=mock_llm_client,
            llama_parse=mock_llama_parse,
            cache=mock_cache,
        )
        
        # Get chunks (should load from cache)
        chunks = document.chunks()
        
        # Verify cached chunks are returned with metadata
        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk.metadata["document_type"] == "guide"
        assert chunk.metadata["information_type"] == "preparation"
        assert chunk.metadata["has_instructions"] is True
        assert chunk.metadata["section_type"] == "procedures"
        
        # Verify LLM was not called (using cache)
        mock_llm_client.responses.create.assert_not_called()

    def test_metadata_validation_warning(
        self, mock_llm_client, mock_llama_parse, mock_cache, capfd
    ):
        """Test that invalid metadata triggers a warning."""
        # Setup mocks for fresh processing
        mock_cache.load_chunks.return_value = None
        mock_cache.load_parsed.return_value = None
        mock_cache.load_original.return_value = None
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = b"Test document"
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.status_code = 200
        mock_response.url = "https://example.com/test.pdf"
        
        # Mock LlamaParse
        mock_page = Mock()
        mock_page.md = "Test content"
        mock_parse_result = Mock()
        mock_parse_result.pages = [mock_page]
        mock_llama_parse.parse.return_value = mock_parse_result
        
        # Mock LLM to return metadata that will fail validation
        # (response will be valid for Pydantic but invalid for our business logic)
        invalid_response = LLMMetadataResponse(
            document_type="guide",
            information_type="response",  # Invalid: response type with "before" phase
            target_audience=["victim"],
            area_type="urban",
            disaster_phase="before"  # Invalid: inconsistent with response type
        )
        mock_llm_response = Mock()
        mock_llm_response.output_parsed = invalid_response
        mock_llm_client.responses.create.return_value = mock_llm_response
        
        # Create document instance
        document = Document(
            url="https://example.com/test.pdf",
            client=mock_llm_client,
            llama_parse=mock_llama_parse,
            cache=mock_cache,
        )
        
        # Process document and capture output
        with patch('requests.get', return_value=mock_response):
            chunks = document.chunks()
        
        # Check that warning was printed
        captured = capfd.readouterr()
        assert "Warning: Invalid metadata extracted" in captured.out
        
        # Verify chunks were still created despite invalid metadata
        assert len(chunks) > 0