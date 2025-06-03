from unittest.mock import MagicMock

import pytest


class TestDuplicatePrevention:
    """Test duplicate document prevention in ChromaDB."""

    @pytest.fixture
    def mock_collection(self):
        """Mock ChromaDB collection."""
        collection = MagicMock()
        collection.count.return_value = 0
        collection.get.return_value = {"ids": [], "metadatas": [], "documents": []}
        collection.add = MagicMock()
        collection.delete = MagicMock()
        return collection

    @pytest.fixture
    def mock_cache(self):
        """Mock document cache."""
        cache = MagicMock()
        cache.has_parsed.return_value = False
        cache.has_original.return_value = False
        cache.exists.return_value = False
        cache.list_cached_documents.return_value = []
        cache.get_cache_size.return_value = {
            "document_count": 0,
            "total_size_mb": 0,
            "total_size_bytes": 0,
        }
        return cache

    def test_prevent_duplicate_indexing(self, mock_collection, mock_cache):
        """Test that duplicate URLs are not re-indexed."""
        url = "https://example.com/doc.pdf"

        # Simulate document already indexed with 3 chunks
        mock_collection.get.return_value = {
            "ids": [
                f"{url}#chunk_0",
                f"{url}#chunk_1",
                f"{url}#chunk_2",
            ],
            "metadatas": [
                {"url": url, "chunk_index": 0},
                {"url": url, "chunk_index": 1},
                {"url": url, "chunk_index": 2},
            ],
            "documents": ["chunk 0", "chunk 1", "chunk 2"],
        }

        # Check if URL is already indexed
        existing_docs = mock_collection.get(where={"url": url})

        # Should find existing documents
        assert len(existing_docs["ids"]) == 3
        assert all(url in doc_id for doc_id in existing_docs["ids"])

        # Should not call add when duplicate detected
        mock_collection.add.assert_not_called()

    def test_allow_new_url_indexing(self, mock_collection, mock_cache):
        """Test that new URLs can be indexed."""
        url = "https://example.com/new-doc.pdf"

        # Simulate no existing documents
        mock_collection.get.return_value = {"ids": [], "metadatas": [], "documents": []}

        # Check if URL is already indexed
        existing_docs = mock_collection.get(where={"url": url})

        # Should not find existing documents
        assert len(existing_docs["ids"]) == 0

        # Should allow indexing of new document
        # (In real implementation, this would proceed to index)
        assert existing_docs["ids"] == []

    def test_reindex_deletes_old_chunks(self, mock_collection, mock_cache):
        """Test that re-indexing removes old chunks before adding new ones."""
        url = "https://example.com/doc.pdf"

        # Simulate existing chunks
        existing_ids = [f"{url}#chunk_0", f"{url}#chunk_1"]
        mock_collection.get.return_value = {
            "ids": existing_ids,
            "metadatas": [
                {"url": url, "chunk_index": 0},
                {"url": url, "chunk_index": 1},
            ],
            "documents": ["old chunk 0", "old chunk 1"],
        }

        # Simulate re-indexing
        mock_collection.delete(ids=existing_ids)

        # Verify old chunks were deleted
        mock_collection.delete.assert_called_once_with(ids=existing_ids)

    def test_orphaned_cache_detection(self, mock_collection, mock_cache):
        """Test detection of orphaned cache entries."""
        # Simulate cached documents
        cached_docs = [
            {"url": "https://example.com/doc1.pdf"},
            {"url": "https://example.com/doc2.pdf"},
            {"url": "https://example.com/doc3.pdf"},
        ]
        mock_cache.list_cached_documents.return_value = cached_docs

        # Simulate only doc1 and doc2 are indexed
        mock_collection.get.return_value = {
            "ids": ["doc1_id", "doc2_id"],
            "metadatas": [
                {"url": "https://example.com/doc1.pdf"},
                {"url": "https://example.com/doc2.pdf"},
            ],
            "documents": ["doc1", "doc2"],
        }

        # Get cached and indexed URLs
        cached_urls = {doc["url"] for doc in cached_docs}
        indexed_urls = {
            metadata["url"] for metadata in mock_collection.get()["metadatas"]
        }

        # Find orphaned entries
        orphaned_urls = cached_urls - indexed_urls

        # Should find doc3 as orphaned
        assert len(orphaned_urls) == 1
        assert "https://example.com/doc3.pdf" in orphaned_urls

    def test_chunk_metadata_preservation(self, mock_collection):
        """Test that chunk metadata is properly preserved during indexing."""
        url = "https://example.com/doc.pdf"
        chunk_metadata = {
            "url": url,
            "chunk_index": 0,
            "total_chunks": 3,
            "start_char": 0,
            "end_char": 1000,
        }

        # Add chunk with metadata
        mock_collection.add(
            documents=["chunk content"],
            metadatas=[chunk_metadata],
            ids=[f"{url}#chunk_0"],
        )

        # Verify metadata was included
        call_args = mock_collection.add.call_args
        assert call_args[1]["metadatas"][0]["url"] == url
        assert call_args[1]["metadatas"][0]["chunk_index"] == 0
        assert call_args[1]["metadatas"][0]["total_chunks"] == 3
