# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Disaster RAG Assistant is an intelligent virtual assistant using RAG (Retrieval-Augmented Generation) architecture to provide personalized, contextual guidance for natural disaster response. It serves victims, residents, and families with real-time safety information, evacuation procedures, and emergency resources in Portuguese.

## Current Project Status (Branch: chunking)

The project is implementing an improved document ingestion system with caching and chunking capabilities. Progress so far:

### Completed Phases:
- **Phase 1** ✅: Document cache infrastructure (`DocumentCache`)
- **Phase 2** ✅: UI integration with download caching
- **Phase 3** ✅: Parsed document caching (avoid LlamaParse API calls)
- **Phase 4** ✅: Document chunking system (`DocumentChunker`)

### Pending Phases:
- **Phase 5**: Integration of chunking with cache
- **Phase 6**: ChromaDB duplicate checking
- **Phase 7**: UI improvements and observability

See `docs/ingestion-improvement-plan.md` for detailed implementation plan.

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

## Pre-Commit Checklist

Before committing changes, always:

1. **Run linting and formatting**:
   ```bash
   uvx ruff check src/
   uvx ruff format src/
   ```

2. **Review and update CLAUDE.md**: Check if any architectural changes, new dependencies, or important implementation details need to be documented in this file.

## Key Files and Structure

### Core Application
- `app.py`: Entry point, configures Langfuse integration and Streamlit pages
- `src/ui/chatbot.py`: Main chat interface with RAG implementation
- `src/ui/settings.py`: Admin interface for indexing new documents (only available in dev environment)
- `.streamlit/secrets.toml.SAMPLE`: Template for API keys configuration

### Document Processing (New in chunking branch)
- `src/retrieval/document.py`: Document processing with LlamaParse and cache integration
- `src/repositories/document_cache.py`: Cache system for documents (original & parsed)
- `src/services/document_chunker.py`: Chunking system for splitting documents

### Cache Structure
```
.cache/documents/
├── {url_hash}/
│   ├── metadata.json    # URL, timestamps, processing status
│   ├── original.bin     # Original downloaded document
│   ├── parsed.md        # LlamaParse output
│   └── chunks.json      # (Future) Chunked document
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

5. **Caching System** (New in chunking branch):
   - Three-level cache: original → parsed → chunks
   - Avoids re-downloads and re-processing
   - Uses URL hash for unique identification
   - Tracks processing status in metadata

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