import os
from datetime import datetime
from urllib.parse import urlparse

import requests
from langfuse.decorators import observe
from langfuse.openai import OpenAI
from llama_cloud_services import LlamaParse
from pydantic import BaseModel, Field

from src.repositories.document_cache import DocumentCache
from src.services.document_chunker import Chunk, DocumentChunker
from src.services.metadata_extractor import MetadataExtractor


class DocumentOutput(BaseModel):
    markdown: str = Field(description="Markdown representation of the document content")
    tags: list[str] = Field(
        default_factory=list, description="List of tags associated with the document"
    )
    chunks: list[Chunk] = Field(
        default_factory=list, description="Document chunks for retrieval"
    )


class Document:
    def __init__(
        self,
        url: str,
        client: OpenAI,
        llama_parse: LlamaParse,
        cache: DocumentCache | None = None,
        chunker: DocumentChunker | None = None,
        metadata_extractor: MetadataExtractor | None = None,
    ):
        self._url: str = url
        self._llm_client: OpenAI = client
        self._document_output: DocumentOutput | None = None
        self._llama_parse: LlamaParse = llama_parse
        self._cache = cache or DocumentCache()
        self._chunker = chunker or DocumentChunker()
        self._metadata_extractor = metadata_extractor or MetadataExtractor(client)

    def markdown(self) -> str:
        if not self._document_output:
            self._read_document()

        return self._document_output.markdown

    def tags(self) -> list[str]:
        if not self._document_output:
            self._read_document()

        return self._document_output.tags

    def chunks(self) -> list[Chunk]:
        if not self._document_output:
            self._read_document()

        return self._document_output.chunks

    def _read_document(self):
        # First, check if we have chunks in cache
        chunks = self._cache.load_chunks(self._url)

        if chunks is not None:
            # We have everything cached
            parsed_content = self._cache.load_parsed(self._url)
            if parsed_content is not None:
                self._document_output = self._create_document(parsed_content, chunks)
                self._cache._update_metadata(
                    self._url, {"chunks_loaded_from_cache": datetime.now().isoformat()}
                )
                return

        # If not, check if we have the parsed document in cache
        parsed_content = self._cache.load_parsed(self._url)

        if parsed_content is not None:
            # Use cached parsed content and generate chunks
            chunks = self._generate_chunks(parsed_content)
            self._document_output = self._create_document(parsed_content, chunks)
            self._cache._update_metadata(
                self._url, {"parsed_loaded_from_cache": datetime.now().isoformat()}
            )
            return

        # If not, check if we have the original document in cache
        content_bytes = self._cache.load_original(self._url)

        if content_bytes is None:
            # Download if not in cache with proper headers and timeout
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/pdf,application/octet-stream,*/*',
                'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(
                self._url, 
                headers=headers,
                timeout=(10, 60),  # 10s connect, 60s read timeout
                stream=True  # Stream large files
            )
            response.raise_for_status()
            content_bytes = response.content

            # Save to cache for future use
            self._cache.save_original(self._url, content_bytes)
            self._cache.save_metadata(
                self._url,
                {
                    "content_type": response.headers.get("content-type", ""),
                    "content_length": len(content_bytes),
                    "status_code": response.status_code,
                },
            )

            # Get filename from response
            file_name = self._get_file_name(response)
        else:
            # Get filename from URL when loading from cache
            file_name = self._get_file_name_from_url(self._url)

        # Parse the document with LlamaParse
        result = self._llama_parse.parse(
            content_bytes, extra_info={"file_name": file_name}
        )
        content = "\n".join(page.md for page in result.pages)

        # Save parsed content to cache
        self._cache.save_parsed(self._url, content)

        # Generate chunks
        chunks = self._generate_chunks(content)

        # Create document output
        self._document_output = self._create_document(content, chunks)

    @observe(name="document_chunk_generation")
    def _generate_chunks(self, content: str) -> list[Chunk]:
        """Generate chunks from parsed content and save to cache."""
        # Extract document-level metadata
        document_metadata = self._metadata_extractor.extract_document_metadata(
            content, self._url
        )
        
        # Validate metadata
        if not self._metadata_extractor.validate_metadata(document_metadata):
            print(f"Warning: Invalid metadata extracted for {self._url}")
        
        # Prepare base metadata for chunks
        base_metadata = {
            "url": self._url,
            "url_hash": self._cache.get_document_hash(self._url),
            "chunked_at": datetime.now().isoformat(),
            # Include document-level metadata
            **document_metadata.to_dict(),
        }

        # Generate chunks with base metadata
        chunks = self._chunker.chunk_document(content, base_metadata)
        
        # Enrich each chunk with specific metadata
        for chunk in chunks:
            chunk_metadata = self._metadata_extractor.extract_chunk_metadata(
                chunk.content
            )
            chunk.metadata.update(chunk_metadata)

        # Save chunks to cache
        self._cache.save_chunks(self._url, chunks)

        return chunks

    @classmethod
    def _create_document(
        cls, content: str, chunks: list[Chunk] | None = None
    ) -> DocumentOutput:
        return DocumentOutput(markdown=content, tags=[], chunks=chunks or [])

    @classmethod
    def _get_file_name(cls, response):
        url_path = urlparse(response.url).path
        if url_path and "." in url_path:
            return os.path.basename(url_path)

    @classmethod
    def _get_file_name_from_url(cls, url: str):
        url_path = urlparse(url).path
        if url_path and "." in url_path:
            return os.path.basename(url_path)
        return "document"
