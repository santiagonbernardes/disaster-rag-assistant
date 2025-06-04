"""Integration tests for XML context formatting in the chatbot."""

from unittest.mock import MagicMock, patch

import streamlit as st

from src.ui.chatbot import get_retrieved_documents


class TestXMLContextIntegration:
    """Test XML context formatting integration."""

    def setup_method(self):
        """Setup test fixtures."""
        # Initialize session state
        if "user_profile" not in st.session_state:
            st.session_state.user_profile = "victim"

    @patch("src.ui.chatbot.collection")
    def test_get_retrieved_documents_returns_xml(self, mock_collection):
        """Test that get_retrieved_documents returns XML formatted context."""
        # Mock ChromaDB query results
        mock_collection.return_value.query.return_value = {
            "ids": [["doc1#chunk_0", "doc2#chunk_1"]],
            "distances": [[0.5, 0.8]],
            "documents": [
                [
                    "Durante enchentes, procure locais elevados.",
                    "Em emergências, ligue 193.",
                ]
            ],
            "metadatas": [
                [
                    {
                        "source_authority": "defesa_civil",
                        "urgency_level": "critical",
                        "disaster_category": "flood",
                        "url": "https://defesacivil.gov.br/manual.pdf",
                        "chunk_index": 0,
                        "total_chunks": 3,
                    },
                    {
                        "source_authority": "bombeiros",
                        "urgency_level": "high",
                        "url": "https://bombeiros.gov.br/contatos.pdf",
                        "chunk_index": 1,
                        "total_chunks": 2,
                    },
                ],
            ],
        }

        # Call the function
        result = get_retrieved_documents("ajuda com enchente")

        # Verify XML structure
        assert "<contexto>" in result
        assert "</contexto>" in result
        assert result.count("<documento") == 2
        assert result.count("</documento>") == 2

        # Verify attributes
        assert 'source_authority="defesa_civil"' in result
        assert 'urgency="critical"' in result
        assert 'disaster_type="flood"' in result
        assert 'url="https://defesacivil.gov.br/manual.pdf"' in result

        # Verify content
        assert "Durante enchentes, procure locais elevados." in result
        assert "Em emergências, ligue 193." in result

    @patch("src.ui.chatbot.collection")
    def test_empty_retrieval_returns_empty_string(self, mock_collection):
        """Test that empty retrieval returns empty string, not empty XML."""
        # Mock no results
        mock_collection.return_value.query.return_value = {
            "ids": [[]],
            "distances": [[]],
            "documents": [[]],
            "metadatas": [[]],
        }

        result = get_retrieved_documents("query sem resultados")

        # Should return empty string, not empty XML
        assert result == ""
        assert "<contexto>" not in result

    @patch("src.ui.chatbot.collection")
    def test_xml_escaping_in_content(self, mock_collection):
        """Test that special characters are properly escaped in XML."""
        # Mock results with special characters
        mock_collection.return_value.query.return_value = {
            "ids": [["doc1"]],
            "distances": [[0.5]],
            "documents": [["Texto com <tags> & caracteres especiais > < & 'quotes'"]],
            "metadatas": [
                [
                    {
                        "source_authority": "test_auth",
                        "url": "https://example.com?param=value&other=test",
                    }
                ],
            ],
        }

        result = get_retrieved_documents("test query")

        # Verify content is escaped
        assert "&lt;tags&gt;" in result
        assert "&amp;" in result
        # Verify URL is escaped in attributes
        assert "https://example.com?param=value&amp;other=test" in result

    @patch("src.ui.chatbot.collection")
    def test_missing_metadata_handled_gracefully(self, mock_collection):
        """Test that documents with missing metadata are handled properly."""
        # Mock results with partial metadata
        mock_collection.return_value.query.return_value = {
            "ids": [["doc1", "doc2"]],
            "distances": [[0.5, 0.7]],
            "documents": [
                [
                    "Documento com metadados completos.",
                    "Documento com metadados parciais.",
                ]
            ],
            "metadatas": [
                [
                    {
                        "source_authority": "defesa_civil",
                        "urgency_level": "high",
                        "disaster_category": "fire",
                        "url": "https://example1.com",
                    },
                    {
                        "url": "https://example2.com",
                        # Missing other metadata
                    },
                ],
            ],
        }

        result = get_retrieved_documents("test query")

        # Both documents should be included
        assert result.count("<documento") == 2

        # First document has all attributes
        assert 'source_authority="defesa_civil"' in result
        assert 'urgency="high"' in result
        assert 'disaster_type="fire"' in result

        # Second document only has URL
        assert 'url="https://example2.com"' in result

    @patch("src.ui.chatbot.collection")
    def test_profile_filtering_affects_results(self, mock_collection):
        """Test that user profile affects document retrieval."""
        # Set profile to victim
        st.session_state.user_profile = "victim"

        # Mock call to verify filter is applied
        mock_query = MagicMock()
        mock_collection.return_value.query = mock_query
        mock_query.return_value = {
            "ids": [[]],
            "distances": [[]],
            "documents": [[]],
            "metadatas": [[]],
        }

        get_retrieved_documents("help")

        # Verify query was called with metadata filter
        mock_query.assert_called_once()
        call_args = mock_query.call_args[1]
        assert "where" in call_args
        assert "$or" in call_args["where"]
