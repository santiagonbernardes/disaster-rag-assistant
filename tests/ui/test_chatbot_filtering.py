import pytest
from unittest.mock import Mock, patch
import streamlit as st
from src.ui.chatbot import get_profile_based_filter, retrieve_documents, get_relevant_documents


class TestChatbotFiltering:
    """Test chatbot metadata filtering functionality."""

    def test_get_profile_based_filter_victim(self):
        """Test metadata filter for victim profile."""
        mock_session_state = Mock()
        mock_session_state.__contains__ = Mock(return_value=True)
        mock_session_state.user_profile = "victim"
        
        with patch.object(st, 'session_state', mock_session_state):
            filter_dict = get_profile_based_filter()
            
        assert filter_dict is not None
        assert "$or" in filter_dict
        
        # Check that victim filter includes response and high urgency
        or_conditions = filter_dict["$or"]
        assert {"information_type": "response"} in or_conditions
        assert {"urgency_level": {"$in": ["critical", "high"]}} in or_conditions
        assert {"target_audience": {"$in": ["victim"]}} in or_conditions

    def test_get_profile_based_filter_resident(self):
        """Test metadata filter for resident profile."""
        mock_session_state = Mock()
        mock_session_state.__contains__ = Mock(return_value=True)
        mock_session_state.user_profile = "resident"
        
        with patch.object(st, 'session_state', mock_session_state):
            filter_dict = get_profile_based_filter()
            
        assert filter_dict is not None
        assert "$or" in filter_dict
        
        # Check that resident filter includes prevention and preparation
        or_conditions = filter_dict["$or"]
        assert {"information_type": {"$in": ["prevention", "preparation"]}} in or_conditions
        assert {"target_audience": {"$in": ["resident", "victim"]}} in or_conditions

    def test_get_profile_based_filter_family(self):
        """Test metadata filter for family profile."""
        mock_session_state = Mock()
        mock_session_state.__contains__ = Mock(return_value=True)
        mock_session_state.user_profile = "family"
        
        with patch.object(st, 'session_state', mock_session_state):
            filter_dict = get_profile_based_filter()
            
        assert filter_dict is not None
        assert "$or" in filter_dict
        
        # Check that family filter includes emergency contacts and recovery
        or_conditions = filter_dict["$or"]
        assert {"target_audience": {"$in": ["family", "victim"]}} in or_conditions
        assert {"has_emergency_contacts": True} in or_conditions
        assert {"information_type": {"$in": ["response", "recovery"]}} in or_conditions

    def test_get_profile_based_filter_no_profile(self):
        """Test metadata filter when no profile is set."""
        mock_session_state = Mock()
        mock_session_state.__contains__ = Mock(return_value=False)
        
        with patch.object(st, 'session_state', mock_session_state):
            filter_dict = get_profile_based_filter()
            
        assert filter_dict is None

    def test_retrieve_documents_with_filter(self):
        """Test document retrieval with metadata filter."""
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "ids": [["doc1", "doc2"]],
            "distances": [[0.5, 0.8]],
            "documents": [["Document 1 content", "Document 2 content"]],
            "metadatas": [[{"url": "url1", "document_type": "guide"}, {"url": "url2", "document_type": "manual"}]]
        }
        
        metadata_filter = {"document_type": "guide"}
        
        with patch('src.ui.chatbot.collection', return_value=mock_collection):
            result = retrieve_documents("test query", metadata_filter)
        
        # Verify query was called with correct parameters
        mock_collection.query.assert_called_once_with(
            query_texts="test query",
            n_results=5,
            where=metadata_filter
        )
        
        assert result["ids"] == [["doc1", "doc2"]]

    def test_retrieve_documents_without_filter(self):
        """Test document retrieval without metadata filter."""
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "ids": [["doc1", "doc2"]],
            "distances": [[0.5, 0.8]],
            "documents": [["Document 1 content", "Document 2 content"]],
            "metadatas": [[{"url": "url1"}, {"url": "url2"}]]
        }
        
        with patch('src.ui.chatbot.collection', return_value=mock_collection):
            result = retrieve_documents("test query")
        
        # Verify query was called without where clause
        mock_collection.query.assert_called_once_with(
            query_texts="test query",
            n_results=5
        )

    def test_get_relevant_documents_with_enriched_metadata(self):
        """Test document filtering with enriched metadata."""
        documents = {
            "ids": [["url1#chunk_0", "url2#chunk_1"]],
            "distances": [[0.5, 0.8]],
            "documents": [["Document 1 content", "Document 2 content"]],
            "metadatas": [[
                {
                    "url": "url1",
                    "chunk_index": 0,
                    "total_chunks": 2,
                    "document_type": "guide",
                    "information_type": "preparation",
                    "target_audience": ["resident"],
                    "urgency_level": "medium",
                    "confidence_score": 0.85
                },
                {
                    "url": "url2", 
                    "chunk_index": 1,
                    "total_chunks": 3,
                    "document_type": "manual",
                    "information_type": "response",
                    "target_audience": ["victim"],
                    "urgency_level": "high",
                    "confidence_score": 0.92
                }
            ]]
        }
        
        relevant_docs = get_relevant_documents(documents)
        
        assert len(relevant_docs) == 2
        
        # Check first document
        first_doc = relevant_docs[0]
        assert first_doc["url"] == "url1"
        assert first_doc["content"] == "Document 1 content"
        assert first_doc["chunk_info"] == "(Trecho 1 de 2)"
        
        # Check second document  
        second_doc = relevant_docs[1]
        assert second_doc["url"] == "url2"
        assert second_doc["content"] == "Document 2 content"
        assert second_doc["chunk_info"] == "(Trecho 2 de 3)"

    def test_get_relevant_documents_filters_by_distance(self):
        """Test that documents are filtered by similarity threshold."""
        documents = {
            "ids": [["url1#chunk_0", "url2#chunk_1", "url3#chunk_0"]],
            "distances": [[0.5, 0.8, 1.5]],  # Third document exceeds threshold
            "documents": [["Document 1", "Document 2", "Document 3"]],
            "metadatas": [[
                {"url": "url1", "chunk_index": 0, "total_chunks": 1},
                {"url": "url2", "chunk_index": 1, "total_chunks": 2},
                {"url": "url3", "chunk_index": 0, "total_chunks": 1}
            ]]
        }
        
        relevant_docs = get_relevant_documents(documents)
        
        # Only first two documents should pass similarity threshold (< 1.3)
        assert len(relevant_docs) == 2
        assert relevant_docs[0]["url"] == "url1"
        assert relevant_docs[1]["url"] == "url2"