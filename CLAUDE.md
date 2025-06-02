# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Disaster RAG Assistant is an intelligent virtual assistant using RAG (Retrieval-Augmented Generation) architecture to provide personalized, contextual guidance for natural disaster response. It serves victims, residents, and families with real-time safety information, evacuation procedures, and emergency resources in Portuguese.

## Current Project Status

The project has completed implementation of an improved document ingestion system with caching and chunking capabilities. Key features include:

- **Document Cache Infrastructure**: File-based caching system for original documents, parsed content, and chunks
- **UI Integration**: Settings interface with progress tracking and cache management
- **Parsed Document Caching**: Avoids redundant LlamaParse API calls
- **Document Chunking System**: Configurable text splitting with overlap for better retrieval
- **ChromaDB Integration**: Duplicate checking and cache synchronization
- **Enhanced UI**: Progress bars, detailed logging, and cache statistics

## Architecture

The application uses:
- **Streamlit** for the web interface with multi-page navigation
- **OpenAI API** for language model generation
- **ChromaDB** for vector storage and semantic search
- **LlamaParse** for document parsing and extraction
- **Langfuse** for observability and prompt management

Key architectural decisions:
- RAG pattern: Retrieves relevant documents from ChromaDB based on user queries, then augments LLM responses with this context
- User profiles (victim/resident/family) determine which prompt template to use from Langfuse
- Documents are indexed with embeddings for semantic search with a similarity threshold of 1.3

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

### Document Processing
- `src/retrieval/document.py`: Document processing with LlamaParse and cache integration
- `src/repositories/document_cache.py`: Cache system for documents (original, parsed & chunks)
- `src/services/document_chunker.py`: Chunking system for splitting documents

### Cache Structure
```
.cache/documents/
├── {url_hash}/
│   ├── metadata.json    # URL, timestamps, processing status
│   ├── original.bin     # Original downloaded document
│   ├── parsed.md        # LlamaParse output
│   └── chunks.json      # Chunked document segments
```

## Important Implementation Details

1. **SQLite Compatibility**: The app includes a workaround for ChromaDB's SQLite issues on Streamlit Cloud using pysqlite3-binary

2. **Session Management**: Uses Streamlit session state to maintain:
   - User profile selection
   - Chat history via OpenAI response IDs
   - Langfuse prompt caching
   - Unique session IDs for tracking

3. **Document Retrieval**: 
   - Queries ChromaDB for top 2 most similar documents
   - Filters results by distance threshold (< 1.3)
   - Formats retrieved documents for prompt augmentation

4. **Environment-based Features**: Settings page for document indexing only appears when `langfuse_environment` is set to "dev"

5. **Caching System**:
   - Three-level cache: original → parsed → chunks
   - Avoids re-downloads and re-processing
   - Uses URL hash for unique identification
   - Tracks processing status in metadata
   - ChromaDB duplicate checking prevents redundant indexing
   - Cache management UI with cleanup options

6. **Chunking Configuration**:
   - Default chunk size: 1000 characters
   - Default overlap: 200 characters
   - Preserves sentence boundaries
   - Maintains chunk position tracking

## Configuration

Copy `.streamlit/secrets.toml.SAMPLE` to `.streamlit/secrets.toml` and fill in your API keys:
- OpenAI API key for LLM generation
- Langfuse keys for observability and prompt management
- LlamaCloud API key for document parsing

## Development Tools and Best Practices

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