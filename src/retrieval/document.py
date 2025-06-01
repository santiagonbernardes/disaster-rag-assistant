import os
from urllib.parse import urlparse

import requests
from langfuse.openai import OpenAI
from llama_cloud_services import LlamaParse
from pydantic import BaseModel, Field


class DocumentOutput(BaseModel):
    markdown: str = Field(description="Markdown representation of the document content")
    tags: list[str] = Field(
        default_factory=list, description="List of tags associated with the document"
    )


class Document:
    def __init__(self, url: str, client: OpenAI, llama_parse: LlamaParse):
        self._url: str = url
        self._llm_client: OpenAI = client
        self._document_output: DocumentOutput | None = None
        self._llama_parse: LlamaParse = llama_parse

    def markdown(self) -> str:
        if not self._document_output:
            self._read_document()

        return self._document_output.markdown

    def tags(self) -> list[str]:
        if not self._document_output:
            self._read_document()

        return self._document_output.tags

    def _read_document(self):
        response = requests.get(self._url)
        response.raise_for_status()
        content_bytes = response.content
        file_name = self._get_file_name(response)
        result = self._llama_parse.parse(
            content_bytes, extra_info={"file_name": file_name}
        )
        content = "\n".join(page.md for page in result.pages)
        with open(f"{file_name.split('.')[0]}.md", "w") as f:
            f.write(content)
        self._document_output = self._create_document(content)

    @classmethod
    def _create_document(cls, content: str) -> DocumentOutput:
        return DocumentOutput(markdown=content, tags=[])

    @classmethod
    def _get_file_name(cls, response):
        url_path = urlparse(response.url).path
        if url_path and "." in url_path:
            return os.path.basename(url_path)
