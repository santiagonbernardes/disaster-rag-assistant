import sys

# Fix for ChromaDB SQLite compatibility on Streamlit Cloud
try:
    import pysqlite3

    sys.modules["sqlite3"] = pysqlite3
except ImportError:
    pass

import chromadb
import streamlit as st
import tiktoken
from langfuse.openai import OpenAI
from llama_cloud_services import LlamaParse

from src.repositories.document_cache import DocumentCache
from src.retrieval.document import Document

st.header("Settings")

# Initialize cache
cache = DocumentCache()

client = chromadb.PersistentClient(path=".db/chroma")
collection = client.get_or_create_collection(name="disaster-documents")

with st.form("settings_form", border=True):
    if "count" not in st.session_state:
        st.session_state.count = collection.count()

    input_col, button_col = st.columns([4, 1], vertical_alignment="bottom")
    with input_col:
        url = st.text_input("URL")

    with button_col:
        if st.form_submit_button("Index", use_container_width=True):
            # Check cache status
            has_parsed = cache.has_parsed(url)
            has_original = cache.has_original(url)

            # Determine processing message
            if has_parsed:
                status_msg = "📄 Loading parsed document from cache..."
            elif has_original:
                status_msg = "🔄 Processing cached document with LlamaParse..."
            else:
                status_msg = "⬇️ Downloading and processing document..."

            with st.spinner(status_msg):
                document = Document(
                    url,
                    client=OpenAI(api_key=st.secrets["openai_api_key"]),
                    llama_parse=LlamaParse(
                        api_key=st.secrets["llama_cloud_api_key"], language="pt"
                    ),
                    cache=cache,
                )

                # Process document
                markdown_content = document.markdown()

                # Add to ChromaDB
                collection.add(
                    documents=[markdown_content],
                    metadatas=[{"url": url}],
                    ids=[url],
                )

                # Show appropriate success message
                if has_parsed:
                    st.success("✅ Document loaded from parsed cache (no API calls)!")
                elif has_original:
                    st.success("✅ Document processed from cached original!")
                else:
                    st.success("✅ Document downloaded, processed and cached!")

with st.container(border=True):
    st.markdown("### Indexed Documents")
    st.markdown(f"Total documents indexed: {collection.count()}")

    collection_data = collection.get()

    documents = collection_data["documents"]
    ids = collection_data["ids"]
    enconding = tiktoken.encoding_for_model("gpt-4")
    for document, doc_id in zip(documents, ids, strict=False):
        num_token = len(enconding.encode(document))
        # Check if document is in cache
        cache_status = "📁 Cached" if cache.exists(doc_id) else "☁️ Not cached"
        with st.expander(
            f"Tokens: {num_token}, Url: {doc_id} | {cache_status}", expanded=False
        ):
            st.write(document)

# Cache statistics section
with st.container(border=True):
    st.markdown("### Cache Statistics")
    cache_stats = cache.get_cache_size()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Cached Documents", cache_stats["document_count"])
    with col2:
        st.metric("Cache Size", f"{cache_stats['total_size_mb']} MB")
    with col3:
        avg_size = (
            f"{cache_stats['total_size_mb'] / cache_stats['document_count']:.2f} MB"
            if cache_stats["document_count"] > 0
            else "0 MB"
        )
        st.metric("Avg Size per Doc", avg_size)
