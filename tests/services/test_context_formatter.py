"""Tests for the ContextFormatter service."""

from src.services.context_formatter import ContextFormatter


class TestContextFormatter:
    """Test cases for ContextFormatter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ContextFormatter()

    def test_format_empty_documents(self):
        """Test formatting with no documents."""
        result = self.formatter.format_documents_as_xml([])
        assert result == "<contexto>\n</contexto>"

    def test_format_single_document_with_metadata(self):
        """Test formatting a single document with full metadata."""
        documents = [
            {
                "content": "Durante enchentes, procure locais elevados.",
                "metadata": {
                    "source_authority": "defesa_civil",
                    "urgency_level": "critical",
                    "disaster_category": "flood",
                    "url": "https://defesacivil.gov.br/manual.pdf",
                    "document_type": "manual",
                    "target_audience": "victim",
                },
            }
        ]

        result = self.formatter.format_documents_as_xml(documents)

        # Check structure
        assert "<contexto>" in result
        assert "</contexto>" in result
        assert "<documento" in result
        assert "</documento>" in result

        # Check attributes - only essential ones should be included
        assert 'source_authority="defesa_civil"' in result
        assert 'urgency="critical"' in result
        assert 'disaster_type="flood"' in result
        assert 'url="https://defesacivil.gov.br/manual.pdf"' in result
        # These should NOT be included to avoid confusing the LLM
        assert 'doc_type="manual"' not in result
        assert 'audience="victim"' not in result

        # Check content
        assert "Durante enchentes, procure locais elevados." in result

    def test_format_multiple_documents(self):
        """Test formatting multiple documents."""
        documents = [
            {
                "content": "Primeiro documento.",
                "metadata": {"source_authority": "bombeiros", "urgency_level": "high"},
            },
            {
                "content": "Segundo documento.",
                "metadata": {
                    "source_authority": "defesa_civil",
                    "urgency_level": "medium",
                },
            },
        ]

        result = self.formatter.format_documents_as_xml(documents)

        # Count documento elements
        assert result.count("<documento") == 2
        assert result.count("</documento>") == 2

        # Check both contents are present
        assert "Primeiro documento." in result
        assert "Segundo documento." in result

    def test_sanitize_xml_content(self):
        """Test XML content sanitization."""
        documents = [
            {
                "content": "Texto com <tags> & caracteres especiais > < & 'quotes'",
                "metadata": {"url": "https://example.com"},
            }
        ]

        result = self.formatter.format_documents_as_xml(documents)

        # Check that special characters are escaped
        assert "&lt;tags&gt;" in result
        assert "&amp;" in result
        assert "&gt;" in result
        assert "&lt;" in result

    def test_sanitize_attribute_values(self):
        """Test XML attribute sanitization."""
        documents = [
            {
                "content": "Conteúdo normal",
                "metadata": {
                    "source_authority": 'authority_with_"quotes"',
                    "url": "https://example.com?param=value&other=test",
                },
            }
        ]

        result = self.formatter.format_documents_as_xml(documents)

        # Check that quotes in attributes are escaped
        assert 'source_authority="authority_with_&quot;quotes&quot;"' in result
        assert 'url="https://example.com?param=value&amp;other=test"' in result

    def test_missing_metadata(self):
        """Test handling documents with missing metadata."""
        documents = [
            {
                "content": "Documento sem metadados",
                "metadata": {},
            }
        ]

        result = self.formatter.format_documents_as_xml(documents)

        # Should still create documento element without attributes
        assert "<documento>" in result
        assert "Documento sem metadados" in result

    def test_partial_metadata(self):
        """Test documents with partial metadata."""
        documents = [
            {
                "content": "Conteúdo parcial",
                "metadata": {
                    "url": "https://example.com",
                    "non_mapped_field": "ignored",
                    "urgency_level": "high",
                    "document_type": "manual",  # Should be ignored
                    "target_audience": "victim",  # Should be ignored
                },
            }
        ]

        result = self.formatter.format_documents_as_xml(documents)

        # Should include only essential mapped fields
        assert 'url="https://example.com"' in result
        assert 'urgency="high"' in result
        assert "non_mapped_field" not in result
        assert "document_type" not in result
        assert "target_audience" not in result

    def test_format_from_chromadb_results(self):
        """Test formatting directly from ChromaDB-style results."""
        documents = ["Conteúdo 1", "Conteúdo 2"]
        metadatas = [
            {"source_authority": "bombeiros", "urgency_level": "critical"},
            {"source_authority": "defesa_civil", "disaster_category": "flood"},
        ]

        result = self.formatter.format_from_chromadb_results(documents, metadatas)

        # Check both documents are formatted
        assert result.count("<documento") == 2
        assert "Conteúdo 1" in result
        assert "Conteúdo 2" in result
        assert 'source_authority="bombeiros"' in result
        assert 'disaster_type="flood"' in result

    def test_special_characters_in_content(self):
        """Test handling of special Portuguese characters."""
        documents = [
            {
                "content": "Atenção: evacuação imediata! Não há tempo.",
                "metadata": {"urgency_level": "critical"},
            }
        ]

        result = self.formatter.format_documents_as_xml(documents)

        # Portuguese characters should be preserved
        assert "Atenção: evacuação imediata! Não há tempo." in result

    def test_attribute_order_consistency(self):
        """Test that attributes appear in a consistent order."""
        documents = [
            {
                "content": "Test",
                "metadata": {
                    "url": "https://test.com",
                    "source_authority": "test_auth",
                    "urgency_level": "high",
                    "disaster_category": "flood",
                },
            }
        ]

        # Format multiple times to ensure consistency
        results = [self.formatter.format_documents_as_xml(documents) for _ in range(3)]

        # All results should be identical
        assert all(r == results[0] for r in results)
