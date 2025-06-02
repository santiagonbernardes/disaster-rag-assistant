import os
from datetime import datetime
from urllib.parse import urlparse

import requests
from langfuse.openai import OpenAI
from llama_cloud_services import LlamaParse
from pydantic import BaseModel, Field

from src.repositories.document_cache import DocumentCache


class DocumentOutput(BaseModel):
    markdown: str = Field(description="Markdown representation of the document content")
    tags: list[str] = Field(
        default_factory=list, description="List of tags associated with the document"
    )


class Document:
    def __init__(
        self,
        url: str,
        client: OpenAI,
        llama_parse: LlamaParse,
        cache: DocumentCache | None = None,
    ):
        self._url: str = url
        self._llm_client: OpenAI = client
        self._document_output: DocumentOutput | None = None
        self._llama_parse: LlamaParse = llama_parse
        self._cache = cache or DocumentCache()

    def markdown(self) -> str:
        if not self._document_output:
            self._read_document()

        return self._document_output.markdown

    def tags(self) -> list[str]:
        if not self._document_output:
            self._read_document()

        return self._document_output.tags

    def _read_document(self):
        # First, check if we have the parsed document in cache
        parsed_content = self._cache.load_parsed(self._url)

        if parsed_content is not None:
            # Use cached parsed content
            self._document_output = self._create_document(parsed_content)
            self._cache._update_metadata(
                self._url, {"parsed_loaded_from_cache": datetime.now().isoformat()}
            )
            return

        # If not, check if we have the original document in cache
        content_bytes = self._cache.load_original(self._url)

        if content_bytes is None:
            # Download if not in cache
            response = requests.get(self._url)
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

        # Create document output
        self._document_output = self._create_document(content)

    @classmethod
    def _create_document(cls, content: str) -> DocumentOutput:
        return DocumentOutput(markdown=content, tags=[])

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
