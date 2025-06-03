from unittest.mock import Mock, patch

import pytest

from src.services.metadata_extractor import (
    DocumentMetadata,
    LLMMetadataResponse,
    MetadataExtractor,
)


class TestMetadataExtractor:
    """Test cases for MetadataExtractor service."""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock OpenAI client for testing."""
        return Mock()

    @pytest.fixture
    def extractor(self, mock_llm_client):
        """MetadataExtractor instance for testing."""
        return MetadataExtractor(mock_llm_client)

    def test_deterministic_extraction_defesa_civil_url(self, extractor):
        """Test deterministic extraction from Defesa Civil URL."""
        url = "https://www.defesacivil.gov.br/manual-enchentes.pdf"
        content = (
            "Este manual sobre enchentes contém procedimentos de evacuação urgente."
        )

        result = extractor._extract_deterministic(content, url)

        assert result["source_authority"] == "defesa_civil"
        assert result["authority_level"] == "federal"
        assert "flood" in result["disaster_categories"]
        assert result["urgency_level"] == "critical"
        assert result["has_instructions"] is False  # No numbered steps

    def test_deterministic_extraction_disaster_keywords(self, extractor):
        """Test disaster category detection from keywords."""
        content = "Procedimentos para incêndio florestal e deslizamento de terra."
        url = "https://example.com/manual.pdf"

        result = extractor._extract_deterministic(content, url)

        assert "fire" in result["disaster_categories"]
        assert "landslide" in result["disaster_categories"]

    def test_deterministic_extraction_urgency_levels(self, extractor):
        """Test urgency level detection."""
        test_cases = [
            ("evacuação imediata necessária", "critical"),
            ("alerta para região", "high"),
            ("orientação preventiva", "medium"),
            ("informação geral", "low"),
        ]

        for content, expected_level in test_cases:
            result = extractor._extract_deterministic(content, "https://example.com")
            assert result["urgency_level"] == expected_level

    def test_deterministic_extraction_structural_elements(self, extractor):
        """Test detection of structural elements."""
        content = """
        1. Primeiro passo do procedimento
        2. Segundo passo
        
        Contatos de emergência: 193, 190
        Localização: Rua das Flores, 123
        """

        result = extractor._extract_deterministic(content, "https://example.com")

        assert result["has_instructions"] is True
        assert result["has_emergency_contacts"] is True
        assert result["has_maps"] is True

    def test_chunk_metadata_extraction(self, extractor):
        """Test chunk-specific metadata extraction."""
        chunk_content = """
        Procedimentos de evacuação:
        1. Mantenha a calma
        2. Siga as orientações
        Telefone de emergência: 193
        """

        result = extractor.extract_chunk_metadata(chunk_content)

        assert result["section_type"] == "procedures"
        assert result["has_emergency_contacts"] is True
        assert result["has_instructions"] is True
        assert result["instruction_density"] > 0

    @patch("src.services.metadata_extractor.langfuse_context")
    def test_llm_extraction_success(
        self, mock_langfuse_context, extractor, mock_llm_client
    ):
        """Test successful LLM metadata extraction."""
        # Mock Langfuse prompt
        mock_prompt = Mock()
        mock_prompt.config = {"model": "gpt-3.5-turbo", "temperature": 0.1}
        mock_prompt.compile.return_value = "Test prompt"
        mock_langfuse_context.client_instance.get_prompt.return_value = mock_prompt

        # Mock LLM response
        mock_response = Mock()
        mock_response.output_parsed = LLMMetadataResponse(
            document_type="manual",
            information_type="response",
            disaster_category="flood",
            target_audience="victim",
            area_type="urban",
            disaster_phase="during",
        )
        mock_response.model = "gpt-3.5-turbo"
        mock_response.usage = {"total_tokens": 100}
        mock_llm_client.responses.parse.return_value = mock_response

        content = "Manual de evacuação para enchentes em área urbana."

        result = extractor._extract_with_llm(content)

        assert isinstance(result, LLMMetadataResponse)
        assert result.document_type == "manual"
        assert result.information_type == "response"
        assert result.target_audience == "victim"
        assert result.area_type == "urban"
        assert result.disaster_phase == "during"

    def test_llm_extraction_failure(self, extractor, mock_llm_client):
        """Test LLM extraction failure handling."""
        # Mock LLM failure
        mock_llm_client.responses.create.side_effect = Exception("API Error")

        content = "Some content"

        result = extractor._extract_with_llm(content)

        assert result is None

    def test_confidence_calculation(self, extractor):
        """Test confidence score calculation."""
        metadata = {
            "source_authority": "defesa_civil",
            "disaster_categories": ["flood"],
            "has_emergency_contacts": True,
            "has_instructions": True,
        }

        # Test with long content
        long_content = " ".join(["word"] * 600)
        confidence = extractor._calculate_confidence(metadata, long_content)

        assert confidence == 1.0  # Should hit max confidence

        # Test with short content
        short_content = "short text"
        confidence = extractor._calculate_confidence({}, short_content)

        assert confidence == 0.0  # No metadata, short content

    def test_extract_document_metadata_integration(self, extractor, mock_llm_client):
        """Test full document metadata extraction."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.output_parsed = LLMMetadataResponse(
            document_type="guide",
            information_type="preparation",
            disaster_category="flood",
            target_audience="resident",
            area_type="general",
            disaster_phase="before",
        )
        mock_llm_client.responses.create.return_value = mock_response

        url = "https://www.defesacivil.gov.br/enchentes.pdf"
        content = "Guia de preparação para enchentes com orientações preventivas."

        result = extractor.extract_document_metadata(content, url)

        assert isinstance(result, DocumentMetadata)
        assert result.document_type == "guide"
        assert result.information_type == "preparation"
        assert result.target_audience == "resident"
        assert result.source_authority == "defesa_civil"
        assert result.authority_level == "federal"
        assert result.disaster_category == "flood"
        assert result.urgency_level == "medium"
        assert result.confidence_score > 0
        assert result.extraction_timestamp is not None

    def test_metadata_to_dict(self):
        """Test DocumentMetadata to_dict conversion."""
        metadata = DocumentMetadata(
            document_type="manual",
            disaster_category="flood",
            information_type="response",
            target_audience="victim",
            urgency_level="high",
            disaster_phase="during",
            source_authority="defesa_civil",
            confidence_score=0.85,
            extraction_timestamp="2024-01-01T00:00:00",
        )

        result = metadata.to_dict()

        assert result["document_type"] == "manual"
        assert result["disaster_category"] == "flood"
        assert result["confidence_score"] == 0.85
        assert "extraction_timestamp" in result

    def test_metadata_validation_valid(self, extractor):
        """Test metadata validation with valid metadata."""
        metadata = DocumentMetadata(
            document_type="guide",
            disaster_category="flood",
            information_type="preparation",
            target_audience="resident",
            urgency_level="medium",
            disaster_phase="before",
            confidence_score=0.8,
            extraction_timestamp="2024-01-01T00:00:00",
        )

        assert extractor.validate_metadata(metadata) is True

    def test_metadata_validation_invalid_consistency(self, extractor):
        """Test metadata validation with invalid consistency."""
        # Invalid: response type with before phase
        metadata = DocumentMetadata(
            document_type="guide",
            disaster_category="flood",
            information_type="response",
            target_audience="victim",
            urgency_level="high",
            disaster_phase="before",  # Inconsistent with response type
            confidence_score=0.8,
            extraction_timestamp="2024-01-01T00:00:00",
        )

        assert extractor.validate_metadata(metadata) is False

    def test_metadata_validation_invalid_urgency_no_categories(self, extractor):
        """Test metadata validation with high urgency but no disaster categories."""
        metadata = DocumentMetadata(
            document_type="guide",
            disaster_category="general",  # Invalid: general with high urgency
            information_type="response",
            target_audience="victim",
            urgency_level="critical",  # High urgency requires specific category
            disaster_phase="during",
            confidence_score=0.8,
            extraction_timestamp="2024-01-01T00:00:00",
        )

        assert extractor.validate_metadata(metadata) is False
