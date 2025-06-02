import hashlib
import json
from datetime import datetime
from pathlib import Path


class DocumentCache:
    """Manages document caching on disk to avoid reprocessing."""

    def __init__(self, cache_dir: Path | str = ".cache/documents"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_document_hash(self, url: str) -> str:
        """Generate a unique hash for the URL."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def get_document_path(self, url: str) -> Path:
        """Get the directory path for a specific document."""
        doc_hash = self.get_document_hash(url)
        return self.cache_dir / doc_hash

    def exists(self, url: str) -> bool:
        """Check if any cached data exists for this URL."""
        return self.get_document_path(url).exists()

    def has_original(self, url: str) -> bool:
        """Check if the original document is cached."""
        doc_path = self.get_document_path(url)
        return (doc_path / "original.bin").exists()

    def has_parsed(self, url: str) -> bool:
        """Check if the parsed document is cached."""
        doc_path = self.get_document_path(url)
        return (doc_path / "parsed.md").exists()

    def save_original(self, url: str, content: bytes) -> None:
        """Save the original document content."""
        doc_path = self.get_document_path(url)
        doc_path.mkdir(parents=True, exist_ok=True)

        # Save original content
        (doc_path / "original.bin").write_bytes(content)

        # Update metadata
        self._update_metadata(url, {"original_saved": datetime.now().isoformat()})

    def load_original(self, url: str) -> bytes | None:
        """Load the original document content."""
        doc_path = self.get_document_path(url)
        original_file = doc_path / "original.bin"

        if original_file.exists():
            return original_file.read_bytes()
        return None

    def save_parsed(self, url: str, markdown: str) -> None:
        """Save the parsed markdown content."""
        doc_path = self.get_document_path(url)
        doc_path.mkdir(parents=True, exist_ok=True)

        # Save parsed content
        (doc_path / "parsed.md").write_text(markdown, encoding="utf-8")

        # Update metadata
        self._update_metadata(url, {"parsed_saved": datetime.now().isoformat()})

    def load_parsed(self, url: str) -> str | None:
        """Load the parsed markdown content."""
        doc_path = self.get_document_path(url)
        parsed_file = doc_path / "parsed.md"

        if parsed_file.exists():
            return parsed_file.read_text(encoding="utf-8")
        return None

    def has_chunks(self, url: str) -> bool:
        """Check if chunks are cached for this document."""
        doc_path = self.get_document_path(url)
        return (doc_path / "chunks.json").exists()

    def save_chunks(self, url: str, chunks: list) -> None:
        """Save document chunks."""
        doc_path = self.get_document_path(url)
        doc_path.mkdir(parents=True, exist_ok=True)

        # Convert chunks to serializable format
        chunks_data = []
        for chunk in chunks:
            chunk_dict = {
                "content": chunk.content,
                "index": chunk.index,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                "metadata": chunk.metadata,
            }
            chunks_data.append(chunk_dict)

        # Save chunks
        (doc_path / "chunks.json").write_text(
            json.dumps(chunks_data, indent=2), encoding="utf-8"
        )

        # Update metadata
        self._update_metadata(
            url,
            {"chunks_saved": datetime.now().isoformat(), "chunk_count": len(chunks)},
        )

    def load_chunks(self, url: str) -> list | None:
        """Load document chunks."""
        doc_path = self.get_document_path(url)
        chunks_file = doc_path / "chunks.json"

        if chunks_file.exists():
            chunks_data = json.loads(chunks_file.read_text(encoding="utf-8"))
            # Import Chunk class for reconstruction
            from src.services.document_chunker import Chunk

            chunks = []
            for chunk_dict in chunks_data:
                chunk = Chunk(
                    content=chunk_dict["content"],
                    index=chunk_dict["index"],
                    start_char=chunk_dict["start_char"],
                    end_char=chunk_dict["end_char"],
                    metadata=chunk_dict["metadata"],
                )
                chunks.append(chunk)
            return chunks
        return None

    def save_metadata(self, url: str, metadata: dict) -> None:
        """Save metadata for a document."""
        doc_path = self.get_document_path(url)
        doc_path.mkdir(parents=True, exist_ok=True)

        metadata_file = doc_path / "metadata.json"
        metadata["url"] = url
        metadata["hash"] = self.get_document_hash(url)
        metadata["updated_at"] = datetime.now().isoformat()

        metadata_file.write_text(json.dumps(metadata, indent=2))

    def load_metadata(self, url: str) -> dict | None:
        """Load metadata for a document."""
        doc_path = self.get_document_path(url)
        metadata_file = doc_path / "metadata.json"

        if metadata_file.exists():
            return json.loads(metadata_file.read_text())
        return None

    def _update_metadata(self, url: str, updates: dict) -> None:
        """Update existing metadata or create new one."""
        metadata = self.load_metadata(url) or {}
        metadata.update(updates)
        self.save_metadata(url, metadata)

    def list_cached_documents(self) -> list[dict]:
        """List all cached documents with their metadata."""
        documents = []
        for doc_dir in self.cache_dir.iterdir():
            if doc_dir.is_dir():
                metadata_file = doc_dir / "metadata.json"
                if metadata_file.exists():
                    metadata = json.loads(metadata_file.read_text())
                    documents.append(metadata)
        return documents

    def clear_cache(self, url: str) -> None:
        """Clear cache for a specific URL."""
        doc_path = self.get_document_path(url)
        if doc_path.exists():
            import shutil

            shutil.rmtree(doc_path)

    def get_cache_size(self) -> dict:
        """Get cache statistics."""
        total_size = 0
        doc_count = 0

        for doc_dir in self.cache_dir.iterdir():
            if doc_dir.is_dir():
                doc_count += 1
                for file in doc_dir.rglob("*"):
                    if file.is_file():
                        total_size += file.stat().st_size

        return {
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "document_count": doc_count,
        }
