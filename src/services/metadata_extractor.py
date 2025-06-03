import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from langfuse.decorators import observe
from langfuse.openai import OpenAI
from pydantic import BaseModel, Field


class LLMMetadataResponse(BaseModel):
    """Structured output for LLM metadata extraction."""
    
    document_type: Literal["manual", "guide", "regulation", "report", "news"] = Field(
        description=(
            "Tipo do documento: manual de instruções, guia orientativo, "
            "regulamentação oficial, relatório técnico ou notícia"
        )
    )
    information_type: Literal[
        "prevention", "preparation", "response", "recovery"
    ] = Field(
        description=(
            "Tipo de informação: prevenção de desastres, preparação para "
            "emergências, resposta durante o evento ou recuperação pós-desastre"
        )
    )
    target_audience: list[
        Literal["victim", "resident", "family", "authority"]
    ] = Field(
        description=(
            "Público-alvo do documento: vítimas diretas, residentes da área, "
            "familiares de afetados ou autoridades responsáveis"
        )
    )
    area_type: Literal["urban", "rural", "coastal", "general"] = Field(
        description=(
            "Tipo de área geográfica: urbana, rural, costeira ou aplicação geral"
        )
    )
    disaster_phase: Literal["before", "during", "after", "general"] = Field(
        description=(
            "Fase do desastre abordada: antes do evento, durante a ocorrência, "
            "após o impacto ou orientação geral"
        )
    )


@dataclass
class DocumentMetadata:
    """Structured metadata for disaster response documents."""
    
    # Content classification
    document_type: str  # manual, guide, regulation, report, news
    disaster_categories: list[str]  # flood, earthquake, fire, landslide, drought
    information_type: str  # prevention, preparation, response, recovery
    target_audience: list[str]  # victim, resident, family, authority
    urgency_level: str  # critical, high, medium, low
    disaster_phase: str  # before, during, after, general
    
    # Geographic scope
    region: str | None = None
    state: str | None = None
    area_type: str | None = None  # urban, rural, coastal
    
    # Source information
    source_authority: str | None = None  # defesa_civil, bombeiros, inpe
    authority_level: str | None = None  # federal, state, municipal
    
    # Structural elements
    has_emergency_contacts: bool = False
    has_instructions: bool = False
    has_maps: bool = False
    
    # Quality metrics
    confidence_score: float = 0.0
    extraction_timestamp: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "document_type": self.document_type,
            "disaster_categories": self.disaster_categories,
            "information_type": self.information_type,
            "target_audience": self.target_audience,
            "urgency_level": self.urgency_level,
            "disaster_phase": self.disaster_phase,
            "region": self.region,
            "state": self.state,
            "area_type": self.area_type,
            "source_authority": self.source_authority,
            "authority_level": self.authority_level,
            "has_emergency_contacts": self.has_emergency_contacts,
            "has_instructions": self.has_instructions,
            "has_maps": self.has_maps,
            "confidence_score": self.confidence_score,
            "extraction_timestamp": self.extraction_timestamp,
        }


class MetadataExtractor:
    """Service for extracting structured metadata from disaster response documents."""
    
    def __init__(self, llm_client: OpenAI):
        """
        Initialize the MetadataExtractor.
        
        Args:
            llm_client: OpenAI client for LLM-based extraction
        """
        self.llm_client = llm_client
        
        # URL patterns for deterministic extraction
        self.url_patterns = {
            "defesacivil.gov.br": {
                "source_authority": "defesa_civil",
                "authority_level": "federal",
            },
            "bombeiros": {
                "source_authority": "bombeiros",
                "authority_level": "state",
            },
            "inpe.br": {"source_authority": "inpe", "authority_level": "federal"},
            "cemaden.gov.br": {
                "source_authority": "cemaden",
                "authority_level": "federal",
            },
            "gov.br": {"authority_level": "federal"},
            ".sp.gov.br": {"state": "sao_paulo", "authority_level": "state"},
            ".rj.gov.br": {"state": "rio_de_janeiro", "authority_level": "state"},
            ".mg.gov.br": {"state": "minas_gerais", "authority_level": "state"},
        }
        
        # Disaster keyword patterns
        self.disaster_keywords = {
            "flood": ["enchente", "inundação", "alagamento", "cheia"],
            "earthquake": ["terremoto", "sismo", "tremor", "abalo"],
            "fire": ["incêndio", "fogo", "queimada", "combustão"],
            "landslide": ["deslizamento", "escorregamento", "movimento de massa"],
            "drought": ["seca", "estiagem", "falta de água"],
            "storm": ["tempestade", "vendaval", "tornado", "ciclone"],
        }
        
        # Urgency indicators
        self.urgency_keywords = {
            "critical": ["imediato", "urgente", "evacuação", "perigo iminente"],
            "high": ["alerta", "atenção", "cuidado", "risco alto"],
            "medium": ["orientação", "prevenção", "preparação"],
            "low": ["informação", "conhecimento", "conscientização"],
        }
    
    @observe(name="metadata_extraction")
    def extract_document_metadata(self, content: str, url: str) -> DocumentMetadata:
        """
        Extract comprehensive metadata from a document.
        
        Args:
            content: The document text content
            url: The document URL
            
        Returns:
            DocumentMetadata object with extracted information
        """
        # Start with deterministic extraction
        deterministic_data = self._extract_deterministic(content, url)
        
        # Enhance with LLM-based extraction
        llm_data = self._extract_with_llm(content)
        
        # Merge results with LLM taking priority for semantic fields
        merged_data = {**deterministic_data}
        if llm_data:
            merged_data.update(llm_data.model_dump())
        
        # Calculate confidence score
        confidence = self._calculate_confidence(merged_data, content)
        
        # Log extraction results for observability
        extraction_stats = {
            "url": url,
            "content_length": len(content),
            "deterministic_fields": len(deterministic_data),
            "llm_extraction_success": llm_data is not None,
            "confidence_score": confidence,
            "disaster_categories_found": len(
                merged_data.get("disaster_categories", [])
            ),
            "has_emergency_contacts": merged_data.get("has_emergency_contacts", False),
            "has_instructions": merged_data.get("has_instructions", False),
        }
        print(f"Metadata extraction stats: {extraction_stats}")
        
        # Create metadata object
        metadata = DocumentMetadata(
            document_type=merged_data.get("document_type", "guide"),
            disaster_categories=merged_data.get("disaster_categories", []),
            information_type=merged_data.get("information_type", "preparation"),
            target_audience=merged_data.get("target_audience", ["resident"]),
            urgency_level=merged_data.get("urgency_level", "medium"),
            disaster_phase=merged_data.get("disaster_phase", "general"),
            region=merged_data.get("region"),
            state=merged_data.get("state"),
            area_type=merged_data.get("area_type"),
            source_authority=merged_data.get("source_authority"),
            authority_level=merged_data.get("authority_level"),
            has_emergency_contacts=merged_data.get("has_emergency_contacts", False),
            has_instructions=merged_data.get("has_instructions", False),
            has_maps=merged_data.get("has_maps", False),
            confidence_score=confidence,
            extraction_timestamp=datetime.now().isoformat(),
        )
        
        return metadata
    
    @observe(name="chunk_metadata_extraction")
    def extract_chunk_metadata(self, chunk_content: str) -> dict:
        """
        Extract chunk-specific metadata.
        
        Args:
            chunk_content: The chunk text content
            
        Returns:
            Dictionary with chunk-specific metadata
        """
        metadata = {}
        
        # Detect section type
        chunk_lower = chunk_content.lower()
        if any(
            word in chunk_lower
            for word in ["introdução", "apresentação", "objetivo"]
        ):
            metadata["section_type"] = "introduction"
        elif any(
            word in chunk_lower
            for word in ["procedimento", "passo", "instrução", "como"]
        ):
            metadata["section_type"] = "procedures"
        elif any(word in chunk_lower for word in ["telefone", "contato", "emergência"]):
            metadata["section_type"] = "contacts"
        elif any(word in chunk_lower for word in ["mapa", "localização", "endereço"]):
            metadata["section_type"] = "maps"
        
        # Detect emergency contacts
        emergency_patterns = [r"1\d{2}", r"\d{3}-\d{4}", r"\(\d{2}\)\s*\d{4,5}-\d{4}"]
        has_emergency_contacts = any(
            re.search(pattern, chunk_content) for pattern in emergency_patterns
        )
        metadata["has_emergency_contacts"] = has_emergency_contacts
        
        # Detect step-by-step instructions
        has_instructions = bool(re.search(r"^\s*\d+\.", chunk_content, re.MULTILINE))
        metadata["has_instructions"] = has_instructions
        
        # Calculate information density
        instruction_words = ["deve", "precisa", "faça", "siga", "evite", "não"]
        instruction_count = sum(
            chunk_content.lower().count(word) for word in instruction_words
        )
        metadata["instruction_density"] = (
            instruction_count / len(chunk_content.split()) if chunk_content else 0
        )
        
        return metadata
    
    @observe(name="deterministic_extraction")
    def _extract_deterministic(self, content: str, url: str) -> dict:
        """Extract metadata using deterministic rules."""
        metadata = {}
        
        # Extract from URL
        for pattern, data in self.url_patterns.items():
            if pattern in url.lower():
                metadata.update(data)
                break
        
        # Extract disaster categories
        content_lower = content.lower()
        detected_disasters = []
        for disaster, keywords in self.disaster_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                detected_disasters.append(disaster)
        metadata["disaster_categories"] = detected_disasters
        
        # Extract urgency level
        for level, keywords in self.urgency_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                metadata["urgency_level"] = level
                break
        
        # Detect structural elements
        emergency_patterns = [r"1\d{2}", r"\d{3}-\d{4}"]
        metadata["has_emergency_contacts"] = any(
            re.search(pattern, content) for pattern in emergency_patterns
        )
        
        metadata["has_instructions"] = bool(
            re.search(r"^\s*\d+\.", content, re.MULTILINE)
        )
        
        map_keywords = ["mapa", "localização", "endereço", "rua", "avenida"]
        metadata["has_maps"] = any(keyword in content_lower for keyword in map_keywords)
        
        return metadata
    
    @observe(name="llm_metadata_extraction")
    def _extract_with_llm(self, content: str) -> LLMMetadataResponse | None:
        """Extract metadata using LLM classification with structured outputs."""
        try:
            # Truncate content if too long
            max_length = 4000
            truncated_content = (
                content[:max_length] if len(content) > max_length else content
            )
            
            prompt = f"""
            Analise este documento de resposta a desastres naturais e extraia
            os metadados solicitados.
            
            Conteúdo do documento:
            {truncated_content}
            """
            
            response = self.llm_client.responses.create(
                model="gpt-4o-mini",
                input=prompt,
                response_format=LLMMetadataResponse
            )

            return response.output_parsed
                
        except Exception as e:
            print(f"LLM extraction failed: {e}")
            return None
    
    def _calculate_confidence(self, metadata: dict, content: str) -> float:
        """Calculate confidence score for extracted metadata."""
        confidence = 0.0
        
        # Higher confidence if we have deterministic matches
        if metadata.get("source_authority"):
            confidence += 0.3
        if metadata.get("disaster_categories"):
            confidence += 0.2
        if metadata.get("has_emergency_contacts"):
            confidence += 0.2
        if metadata.get("has_instructions"):
            confidence += 0.1
        
        # Higher confidence for longer documents
        word_count = len(content.split())
        if word_count > 500:
            confidence += 0.2
        elif word_count > 100:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    @observe(name="metadata_validation")
    def validate_metadata(self, metadata: DocumentMetadata) -> bool:
        """
        Validate extracted metadata for consistency and completeness.
        
        Args:
            metadata: DocumentMetadata object to validate
            
        Returns:
            True if metadata is valid, False otherwise
        """
        # Required fields must be present and valid
        if not metadata.document_type:
            return False
        if not metadata.information_type:
            return False
        if not metadata.target_audience:
            return False
        if not metadata.urgency_level:
            return False
        if not metadata.disaster_phase:
            return False
        
        # Confidence score should be reasonable
        if metadata.confidence_score < 0 or metadata.confidence_score > 1:
            return False
        
        # Disaster categories should not be empty if we have high urgency
        if (
            metadata.urgency_level in ["critical", "high"]
            and not metadata.disaster_categories
        ):
            return False
        
        # Consistency checks
        if (
            metadata.information_type == "response"
            and metadata.disaster_phase == "before"
        ):
            return False
        
        return not (
            metadata.information_type == "prevention"
            and metadata.disaster_phase == "during"
        )