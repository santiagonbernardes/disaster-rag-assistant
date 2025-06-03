# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Disaster RAG Assistant is an intelligent virtual assistant using RAG (Retrieval-Augmented Generation) architecture to provide personalized, contextual guidance for natural disaster response. It serves victims, residents, and families with real-time safety information, evacuation procedures, and emergency resources in Portuguese.

## Current Project Status

The project has completed implementation of a comprehensive metadata extraction system for intelligent document retrieval. Key features include:

- **Metadata Extraction System**: Automatic extraction of structured metadata using deterministic rules and LLM classification
- **Document Cache Infrastructure**: File-based caching system for original documents, parsed content, and enriched chunks
- **UI Integration**: Settings interface with progress tracking and metadata quality validation
- **Intelligent Retrieval**: Profile-based filtering using extracted metadata (victim, resident, family)
- **ChromaDB Integration**: Metadata-enriched indexing with duplicate checking and cache synchronization
- **Langfuse Observability**: Comprehensive tracing of metadata extraction and retrieval processes
- **Enhanced UI**: Progress bars, detailed logging, cache statistics, and metadata validation warnings

## Architecture

The application uses:
- **Streamlit** for the web interface with multi-page navigation
- **OpenAI API** for language model generation
- **ChromaDB** for vector storage and semantic search
- **LlamaParse** for document parsing and extraction
- **Langfuse** for observability and prompt management

Key architectural decisions:
- **Enhanced RAG pattern**: Retrieves relevant documents from ChromaDB using semantic search + metadata filtering, then augments LLM responses with contextually relevant content
- **Intelligent Profiling**: User profiles (victim/resident/family) determine both prompt templates from Langfuse and automatic metadata filtering for document retrieval
- **Metadata-Enhanced Indexing**: Documents are indexed with embeddings + structured metadata (document type, disaster category, urgency level, target audience, etc.)
- **Multi-Stage Filtering**: Similarity threshold of 1.3 combined with profile-based metadata filters for improved precision

## Development Commands

```bash
# Run the application
uv run streamlit run app.py

# Install dependencies
uv sync

# Linting and formatting
uvx ruff check src/
uvx ruff format src/
```

## Development Methodology

### Planning and Implementation Process

For new features or significant changes, follow this proven methodology:

#### 1. Create a Comprehensive Plan
- **Document Location**: Create plan files in `docs/` (e.g., `feature-improvement-plan.md`)
- **Structure**: Include objective, requirements, phases, implementation details, and success metrics
- **Break Down**: Divide into 5-7 manageable phases that can be implemented and tested independently
- **Dependencies**: Clearly identify dependencies between phases

#### 2. Phase-Based Implementation
- **One Phase at a Time**: Complete each phase before moving to the next
- **Incremental Progress**: Each phase should add tangible value and be testable
- **Documentation**: Update progress in plan documents as phases complete
- **Testing**: Run full test suite after each phase completion

#### 3. Status Tracking and Artifacts
- **Todo Management**: Use TodoWrite/TodoRead tools to track tasks within each phase
- **Progress Updates**: Update CLAUDE.md and plan documents with completed phases
- **Real-time Status**: Mark phases as ✅ when completed
- **Artifact Updates**: Keep all project documentation synchronized

#### 4. Feedback Loop Process
- **Commit Early**: Commit each completed phase separately
- **Test Integration**: Verify each phase works with existing functionality  
- **Document Changes**: Update architecture notes and key implementation details
- **Clean Up**: Remove temporary plan files when implementation is complete

#### 5. Post-Implementation Cleanup
- **Remove Plan Files**: Delete temporary implementation plan documents
- **Update Documentation**: Ensure README.md, CLAUDE.md reflect new capabilities
- **Preserve Examples**: Keep useful example code for future reference
- **Final Commit**: Clean commit with updated documentation

### Example Phase Structure
```markdown
### Phase 1: Infrastructure Setup (✅ Deliverable: Core functionality)
- [ ] Create base classes and interfaces
- [ ] Add configuration options  
- [ ] Implement basic functionality
- [ ] Add unit tests

### Phase 2: Integration (✅ Deliverable: Working integration)
- [ ] Connect with existing systems
- [ ] Update UI components
- [ ] Add error handling
- [ ] Integration tests
```

## Pre-Commit Checklist

Before committing changes, always:

1. **Run linting and formatting**:
   ```bash
   uvx ruff check src/
   uvx ruff format src/
   ```

2. **Execute tests**:
   ```bash
   uv run pytest
   ```

3. **Review and update CLAUDE.md**: Check if any architectural changes, new dependencies, or important implementation details need to be documented in this file.

## Key Files and Structure

### Core Application
- `app.py`: Entry point, configures Langfuse integration and Streamlit pages
- `src/ui/chatbot.py`: Main chat interface with RAG implementation
- `src/ui/settings.py`: Admin interface for indexing new documents (only available in dev environment)
- `.streamlit/secrets.toml.SAMPLE`: Template for API keys configuration

### Document Processing & Metadata Extraction
- `src/retrieval/document.py`: Document processing with LlamaParse, cache integration, and metadata extraction
- `src/repositories/document_cache.py`: Cache system for documents (original, parsed & enriched chunks)
- `src/services/document_chunker.py`: Chunking system for splitting documents with metadata support
- `src/services/metadata_extractor.py`: Automatic metadata extraction using deterministic rules and LLM classification

### Cache Structure
```
.cache/documents/
├── {url_hash}/
│   ├── metadata.json    # URL, timestamps, processing status
│   ├── original.bin     # Original downloaded document
│   ├── parsed.md        # LlamaParse output
│   └── chunks.json      # Chunked document segments with enriched metadata
```

## Important Implementation Details

1. **SQLite Compatibility**: The app includes a workaround for ChromaDB's SQLite issues on Streamlit Cloud using pysqlite3-binary

2. **Session Management**: Uses Streamlit session state to maintain:
   - User profile selection
   - Chat history via OpenAI response IDs
   - Langfuse prompt caching
   - Unique session IDs for tracking

3. **Intelligent Document Retrieval**: 
   - Queries ChromaDB for top 5 most similar documents with automatic metadata filtering
   - Profile-based filtering (victim: urgent response info, resident: prevention/preparation, family: contacts/recovery)
   - Filters results by distance threshold (< 1.3) and relevance scoring
   - Formats retrieved documents with metadata context for prompt augmentation

4. **Environment-based Features**: Settings page for document indexing only appears when `langfuse_environment` is set to "dev"

5. **Advanced Caching System**:
   - Three-level cache: original → parsed → enriched chunks with metadata
   - Avoids re-downloads, re-processing, and re-extraction of metadata
   - Uses URL hash for unique identification
   - Tracks processing status and metadata quality in cache metadata
   - ChromaDB duplicate checking prevents redundant indexing
   - Cache management UI with cleanup options and metadata statistics

6. **Metadata Extraction System**:
   - **Deterministic extraction**: URL patterns, text regex, structural elements detection
   - **LLM-based classification**: Document type, disaster category, target audience, urgency level
   - **Validation**: Consistency checks and confidence scoring
   - **Chunk-specific metadata**: Section type, instruction density, emergency contacts detection
   - **Profile-based filtering**: Automatic filtering based on user profile (victim/resident/family)

7. **Enhanced Chunking Configuration**:
   - Default chunk size: 1000 characters
   - Default overlap: 200 characters
   - Preserves sentence boundaries
   - Maintains chunk position tracking
   - Enriches chunks with document-level and chunk-specific metadata

## Configuration

Copy `.streamlit/secrets.toml.SAMPLE` to `.streamlit/secrets.toml` and fill in your API keys:
- OpenAI API key for LLM generation
- Langfuse keys for observability and prompt management
- LlamaCloud API key for document parsing

## Development Tools and Best Practices

### Important File Modification Rules

**CHANGELOG.md**: Do not modify this file directly. The changelog is managed automatically via conventional commits and release automation. Any manual changes will be overwritten during the release process.

### Task Management with Claude Code
When working on complex features, use Claude Code's built-in tools:

```python
# Example: Using TodoWrite for phase tracking
TodoWrite([
    {"id": "1", "content": "Create base infrastructure", "status": "pending", "priority": "high"},
    {"id": "2", "content": "Add UI components", "status": "pending", "priority": "high"},
    {"id": "3", "content": "Implement error handling", "status": "pending", "priority": "medium"}
])

# Update status as work progresses
TodoWrite([
    {"id": "1", "content": "Create base infrastructure", "status": "completed", "priority": "high"},
    {"id": "2", "content": "Add UI components", "status": "in_progress", "priority": "high"},
    {"id": "3", "content": "Implement error handling", "status": "pending", "priority": "medium"}
])
```

### Documentation Standards
- **Plan Files**: Create in `docs/` with clear structure (objective, requirements, phases, success metrics)
- **Progress Tracking**: Update plan files with ✅ markers as phases complete
- **Status Documentation**: Keep CLAUDE.md current with architectural changes
- **Examples**: Preserve useful code examples in `examples/` directory

### Testing Strategy
- **Phase Testing**: Run tests after each phase completion
- **Integration Testing**: Verify new features work with existing functionality
- **Regression Testing**: Ensure no existing functionality is broken
- **Coverage**: Maintain comprehensive test coverage for new features

### Quality Assurance
- **Linting**: Use `uvx ruff check src/` before commits
- **Formatting**: Use `uvx ruff format src/` for consistent code style
- **Type Checking**: Consider adding type hints for complex functions
- **Documentation**: Update docstrings and comments for new functionality

This methodology ensures sustainable development with clear progress tracking, thorough testing, and maintainable code quality.