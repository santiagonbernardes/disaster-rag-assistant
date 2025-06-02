import re
from dataclasses import dataclass


@dataclass
class Chunk:
    """Represents a chunk of text from a document."""

    content: str
    index: int
    start_char: int
    end_char: int
    metadata: dict


class DocumentChunker:
    """Service for splitting documents into semantic chunks."""

    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        """
        Initialize the DocumentChunker.

        Args:
            chunk_size: Target size for each chunk in characters
            overlap: Number of characters to overlap between chunks
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0:
            raise ValueError("overlap must be non-negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size")

        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_document(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """
        Split a document into chunks with overlap.

        Args:
            text: The document text to chunk
            metadata: Optional metadata to include with each chunk

        Returns:
            List of Chunk objects
        """
        if not text:
            return []

        metadata = metadata or {}
        chunks = []

        # Find natural break points (sentences)
        sentences = self._split_into_sentences(text)

        current_chunk = []
        current_size = 0
        start_char = 0

        for sentence in sentences:
            sentence_size = len(sentence)

            # If adding this sentence would exceed chunk size
            if current_size + sentence_size > self.chunk_size and current_chunk:
                # Create chunk from accumulated sentences
                chunk_content = " ".join(current_chunk)
                chunks.append(
                    Chunk(
                        content=chunk_content,
                        index=len(chunks),
                        start_char=start_char,
                        end_char=start_char + len(chunk_content),
                        metadata={
                            **metadata,
                            "chunk_index": len(chunks),
                            "total_chunks": None,  # Will be updated later
                        },
                    )
                )

                # Calculate overlap
                if self.overlap > 0:
                    # Keep some sentences for overlap
                    overlap_size = 0
                    overlap_sentences = []

                    for sent in reversed(current_chunk):
                        overlap_size += len(sent) + 1  # +1 for space
                        if overlap_size <= self.overlap:
                            overlap_sentences.insert(0, sent)
                        else:
                            break

                    current_chunk = overlap_sentences
                    current_size = sum(len(s) + 1 for s in current_chunk) - 1
                    start_char = chunks[-1].end_char - current_size
                else:
                    current_chunk = []
                    current_size = 0
                    start_char = chunks[-1].end_char + 1

            # Add sentence to current chunk
            current_chunk.append(sentence)
            # Add space between sentences
            current_size += sentence_size + (1 if current_chunk else 0)

        # Don't forget the last chunk
        if current_chunk:
            chunk_content = " ".join(current_chunk)
            chunks.append(
                Chunk(
                    content=chunk_content,
                    index=len(chunks),
                    start_char=start_char,
                    end_char=start_char + len(chunk_content),
                    metadata={
                        **metadata,
                        "chunk_index": len(chunks),
                        "total_chunks": None,
                    },
                )
            )

        # Update total_chunks in metadata
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk.metadata["total_chunks"] = total_chunks

        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences using simple heuristics.

        This is a basic implementation. For production, consider using
        libraries like NLTK or spaCy for better sentence segmentation.
        """
        # Replace multiple spaces and newlines with single space
        text = re.sub(r"\s+", " ", text).strip()

        # Split by sentence-ending punctuation followed by space and capital letter
        # This regex looks for: [.!?] followed by space(s) and uppercase letter
        sentence_pattern = r"(?<=[.!?])\s+(?=[A-Z])"
        sentences = re.split(sentence_pattern, text)

        # Clean up sentences
        sentences = [s.strip() for s in sentences if s.strip()]

        # If no sentences found, try simpler approach
        if not sentences:
            # Split by any sentence-ending punctuation
            simple_pattern = r"(?<=[.!?])\s+"
            sentences = re.split(simple_pattern, text)
            sentences = [s.strip() for s in sentences if s.strip()]

        # If still no sentences, split by newlines
        if not sentences:
            sentences = [line.strip() for line in text.split("\n") if line.strip()]

        # If still nothing, return the whole text
        if not sentences and text.strip():
            sentences = [text.strip()]

        return sentences

    def chunk_by_tokens(
        self, text: str, max_tokens: int, tokenizer_func, metadata: dict | None = None
    ) -> list[Chunk]:
        """
        Alternative chunking method based on token count.

        Args:
            text: The document text to chunk
            max_tokens: Maximum tokens per chunk
            tokenizer_func: Function that converts text to tokens
            metadata: Optional metadata to include with each chunk

        Returns:
            List of Chunk objects
        """
        # This is a placeholder for token-based chunking
        # Implementation would depend on the specific tokenizer
        raise NotImplementedError("Token-based chunking not yet implemented")
