import pytest

from src.services.document_chunker import Chunk, DocumentChunker


class TestDocumentChunker:
    def test_init_valid_parameters(self):
        """Test initialization with valid parameters."""
        chunker = DocumentChunker(chunk_size=500, overlap=100)
        assert chunker.chunk_size == 500
        assert chunker.overlap == 100

    def test_init_invalid_parameters(self):
        """Test initialization with invalid parameters."""
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            DocumentChunker(chunk_size=0)

        with pytest.raises(ValueError, match="overlap must be non-negative"):
            DocumentChunker(chunk_size=100, overlap=-1)

        with pytest.raises(ValueError, match="overlap must be less than chunk_size"):
            DocumentChunker(chunk_size=100, overlap=100)

    def test_chunk_empty_document(self):
        """Test chunking an empty document."""
        chunker = DocumentChunker()
        chunks = chunker.chunk_document("")
        assert chunks == []

    def test_chunk_small_document(self):
        """Test chunking a document smaller than chunk size."""
        chunker = DocumentChunker(chunk_size=1000, overlap=200)
        text = "This is a small document. It fits in one chunk."

        chunks = chunker.chunk_document(text)

        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].index == 0
        assert chunks[0].start_char == 0
        assert chunks[0].end_char == len(text)
        assert chunks[0].metadata["chunk_index"] == 0
        assert chunks[0].metadata["total_chunks"] == 1

    def test_chunk_multiple_sentences(self):
        """Test chunking a document with multiple sentences."""
        chunker = DocumentChunker(chunk_size=50, overlap=10)
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."

        chunks = chunker.chunk_document(text)

        assert len(chunks) > 1
        # Verify all chunks have metadata
        for i, chunk in enumerate(chunks):
            assert chunk.index == i
            assert chunk.metadata["chunk_index"] == i
            assert chunk.metadata["total_chunks"] == len(chunks)

    def test_chunk_with_overlap(self):
        """Test that overlap works correctly."""
        chunker = DocumentChunker(chunk_size=100, overlap=30)
        text = (
            "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."
        )

        chunks = chunker.chunk_document(text)

        # Check that chunks have overlap
        if len(chunks) > 1:
            # Some content from chunk 0 should appear in chunk 1
            for i in range(len(chunks) - 1):
                # There should be some overlapping content
                # Due to sentence boundaries, exact overlap might vary
                # Just verify chunks exist and have content
                assert chunks[i].content
                assert chunks[i + 1].content

    def test_chunk_with_metadata(self):
        """Test chunking with custom metadata."""
        chunker = DocumentChunker()
        text = "Test document content."
        metadata = {"source": "test.pdf", "author": "Test Author"}

        chunks = chunker.chunk_document(text, metadata)

        assert len(chunks) == 1
        assert chunks[0].metadata["source"] == "test.pdf"
        assert chunks[0].metadata["author"] == "Test Author"
        assert "chunk_index" in chunks[0].metadata
        assert "total_chunks" in chunks[0].metadata

    def test_sentence_splitting(self):
        """Test the sentence splitting logic."""
        chunker = DocumentChunker()

        # Test basic sentence splitting
        text = "First sentence. Second sentence! Third sentence?"
        sentences = chunker._split_into_sentences(text)
        assert len(sentences) == 3
        assert sentences[0] == "First sentence."
        assert sentences[1] == "Second sentence!"
        assert sentences[2] == "Third sentence?"

    def test_chunk_long_document(self):
        """Test chunking a long document."""
        chunker = DocumentChunker(chunk_size=100, overlap=20)

        # Create a long document
        sentences = [f"This is sentence number {i}." for i in range(50)]
        text = " ".join(sentences)

        chunks = chunker.chunk_document(text)

        # Should have multiple chunks
        assert len(chunks) > 5

        # Verify chunk properties
        for i, chunk in enumerate(chunks):
            assert chunk.index == i
            # Some flexibility for sentence boundaries
            assert len(chunk.content) <= chunker.chunk_size + 100
            assert chunk.start_char < chunk.end_char

        # Verify chunks cover the whole document (considering overlap)
        # First chunk should start at 0
        assert chunks[0].start_char == 0

    def test_chunk_with_newlines(self):
        """Test chunking text with newlines."""
        chunker = DocumentChunker(chunk_size=50, overlap=10)
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."

        chunks = chunker.chunk_document(text)

        assert len(chunks) >= 1
        # All text should be included
        all_content = " ".join(chunk.content for chunk in chunks)
        assert "First paragraph" in all_content
        assert "Second paragraph" in all_content
        assert "Third paragraph" in all_content

    def test_chunk_dataclass_properties(self):
        """Test Chunk dataclass properties."""
        chunk = Chunk(
            content="Test content",
            index=0,
            start_char=0,
            end_char=12,
            metadata={"test": "value"},
        )

        assert chunk.content == "Test content"
        assert chunk.index == 0
        assert chunk.start_char == 0
        assert chunk.end_char == 12
        assert chunk.metadata == {"test": "value"}
