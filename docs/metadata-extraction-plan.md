# Metadata Extraction Implementation Plan

## Objective
Implement automatic metadata extraction for disaster response documents to improve RAG retrieval precision and relevance.

## Requirements
- Extract structured metadata from documents using deterministic rules + LLM
- Enrich chunks with specific metadata for better categorization
- Integrate metadata into ChromaDB indexing pipeline
- Support metadata-based filtering in retrieval system

## Implementation Phases

### Phase 1: Core Infrastructure
**Deliverable**: Basic metadata extraction classes and structure

- [ ] Create `MetadataExtractor` class with OpenAI integration
- [ ] Define metadata schema (document type, disaster category, audience, urgency)
- [ ] Implement deterministic extraction (URL patterns, text regex)
- [ ] Add unit tests for basic extraction
- [ ] Update `Chunk` dataclass to support enriched metadata

### Phase 2: LLM-Based Classification
**Deliverable**: Semantic document classification via LLM

- [ ] Create structured prompts for document classification
- [ ] Implement OpenAI API integration for semantic extraction
- [ ] Add metadata validation and fallback mechanisms
- [ ] Test with real disaster documents
- [ ] Cache LLM responses to avoid reprocessing

### Phase 3: Pipeline Integration
**Deliverable**: Documents processed with enriched metadata

- [ ] Modify `Document._generate_chunks()` to include metadata extraction
- [ ] Update document cache to persist metadata alongside chunks
- [ ] Ensure backward compatibility with existing cached documents
- [ ] Add integration tests for full pipeline
- [ ] Update cache structure documentation

### Phase 4: ChromaDB Integration
**Deliverable**: Vector database with metadata filtering

- [ ] Modify document indexing to include metadata in ChromaDB
- [ ] Update `get_relevant_documents()` to support metadata filters
- [ ] Implement user profile-based automatic filtering
- [ ] Add metadata validation during indexing
- [ ] Test filtered queries and performance

### Phase 5: Settings UI Enhancement
**Deliverable**: User interface for metadata management

- [ ] Add metadata visualization in Settings page
- [ ] Create reprocessing options for existing documents
- [ ] Display metadata extraction statistics
- [ ] Add manual metadata editing capabilities
- [ ] Include metadata quality metrics

## Technical Implementation

### Metadata Schema
```python
{
    "document_type": "manual|guide|regulation|report|news",
    "disaster_categories": ["flood", "earthquake", "fire", "landslide", "drought"],
    "information_type": "prevention|preparation|response|recovery",
    "target_audience": ["victim", "resident", "family", "authority"],
    "urgency_level": "critical|high|medium|low",
    "geographic_scope": {"region": "...", "state": "..."},
    "has_emergency_contacts": true|false,
    "has_instructions": true|false,
    "confidence_score": 0.85
}
```

### Core Classes
```python
class MetadataExtractor:
    def extract_document_metadata(self, content: str, url: str) -> dict
    def extract_chunk_metadata(self, chunk: str) -> dict
    def _deterministic_extraction(self, content: str, url: str) -> dict
    def _llm_extraction(self, content: str) -> dict
```

### Cache Structure
```
.cache/documents/{url_hash}/
├── metadata.json    # Document-level metadata
├── chunks.json      # Chunks with enriched metadata
├── parsed.md        # Parsed content
└── original.bin     # Original document
```

## Success Metrics
- **Extraction Performance**: < 30 seconds per document
- **Success Rate**: > 95% documents processed without errors
- **Classification Accuracy**: > 80% correct automatic classification
- **Retrieval Improvement**: 20% better relevance scores
- **Query Performance**: < 2 seconds response time

## Timeline
- **Phase 1-2**: 1 week (Infrastructure + LLM)
- **Phase 3-4**: 1 week (Integration + ChromaDB)
- **Phase 5**: 3 days (UI enhancements)

**Total**: 2.5 weeks

## Next Steps
1. Start with Phase 1: Create `MetadataExtractor` class
2. Test LLM classification with sample documents
3. Integrate incrementally with existing pipeline
4. Validate performance and accuracy
5. Deploy with monitoring