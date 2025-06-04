"""Context formatter for converting retrieved documents to XML format."""

import html
from typing import Any


class ContextFormatter:
    """Service for formatting retrieved documents as XML context for LLM prompts."""

    # Mapping from ChromaDB metadata fields to XML attributes
    # Only include metadata that is useful for the LLM based on the prompt
    # Additional metadata like document_type, target_audience, area_type, etc.
    # are intentionally excluded to avoid confusing the LLM with unnecessary information
    METADATA_MAPPING = {
        "source_authority": "source_authority",  # Used for citation names
        "urgency_level": "urgency",  # Used to prioritize critical info
        "disaster_category": "disaster_type",  # Provides disaster context
        "url": "url",  # Essential for reference links
    }

    def format_documents_as_xml(self, documents: list[dict[str, Any]]) -> str:
        """
        Format retrieved documents as XML context.

        Args:
            documents: List of document dicts with 'content' and 'metadata'

        Returns:
            XML-formatted string with documento elements
        """
        if not documents:
            return "<contexto>\n</contexto>"

        xml_parts = ["<contexto>"]

        for doc in documents:
            # Extract content and metadata
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})

            # Build XML attributes from metadata
            attributes = self._build_xml_attributes(metadata)

            # Sanitize content for XML
            safe_content = self._sanitize_for_xml(content)

            # Create documento element
            if attributes:
                xml_parts.append(f"  <documento {attributes}>")
            else:
                xml_parts.append("  <documento>")

            xml_parts.append(f"    {safe_content}")
            xml_parts.append("  </documento>")

        xml_parts.append("</contexto>")

        return "\n".join(xml_parts)

    def _build_xml_attributes(self, metadata: dict[str, Any]) -> str:
        """
        Build XML attribute string from metadata.

        Args:
            metadata: Document metadata dictionary

        Returns:
            String of XML attributes like 'source="defesa_civil" urgency="high"'
        """
        attributes = []

        for meta_key, xml_attr in self.METADATA_MAPPING.items():
            if meta_key in metadata and metadata[meta_key]:
                # Sanitize attribute value
                value = str(metadata[meta_key])
                safe_value = self._sanitize_attribute_value(value)
                attributes.append(f'{xml_attr}="{safe_value}"')

        return " ".join(attributes)

    def _sanitize_for_xml(self, text: str) -> str:
        """
        Escape special XML characters in content.

        Args:
            text: Raw text content

        Returns:
            XML-safe text
        """
        # Use html.escape which handles <, >, &, and quotes
        return html.escape(text, quote=False)

    def _sanitize_attribute_value(self, value: str) -> str:
        """
        Sanitize attribute values for XML.

        Args:
            value: Raw attribute value

        Returns:
            Safe attribute value
        """
        # Escape quotes and other special characters
        return html.escape(value, quote=True)

    def format_from_chromadb_results(
        self, documents: list[dict[str, Any]], metadatas: list[dict[str, Any]]
    ) -> str:
        """
        Format documents directly from ChromaDB query results.

        Args:
            documents: List of document contents from ChromaDB
            metadatas: List of metadata dicts from ChromaDB

        Returns:
            XML-formatted string
        """
        formatted_docs = []

        for content, metadata in zip(documents, metadatas, strict=True):
            doc_dict = {"content": content, "metadata": metadata}
            formatted_docs.append(doc_dict)

        return self.format_documents_as_xml(formatted_docs)
