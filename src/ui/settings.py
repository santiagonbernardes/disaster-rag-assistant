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
            # First check if URL is already indexed in ChromaDB
            existing_docs = collection.get(where={"url": url})

            if existing_docs and existing_docs["ids"]:
                st.warning(
                    f"⚠️ Document already indexed with {len(existing_docs['ids'])} "
                    f"{'chunks' if len(existing_docs['ids']) > 1 else 'item'}. "
                    "Use re-index to update."
                )
            else:
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

                    # Process document and get chunks
                    markdown_content = document.markdown()
                    chunks = document.chunks()

                    # Add chunks to ChromaDB
                    if chunks:
                        # Prepare data for ChromaDB
                        documents = []
                        metadatas = []
                        ids = []

                        for chunk in chunks:
                            documents.append(chunk.content)
                            # Include original URL and chunk-specific metadata
                            chunk_metadata = {
                                "url": url,
                                "chunk_index": chunk.index,
                                "total_chunks": chunk.metadata.get(
                                    "total_chunks", len(chunks)
                                ),
                                "start_char": chunk.start_char,
                                "end_char": chunk.end_char,
                            }
                            metadatas.append(chunk_metadata)
                            # Create unique ID for each chunk
                            ids.append(f"{url}#chunk_{chunk.index}")

                        # Add all chunks to ChromaDB
                        collection.add(
                            documents=documents,
                            metadatas=metadatas,
                            ids=ids,
                        )
                    else:
                        # Fallback to full document if no chunks
                        collection.add(
                            documents=[markdown_content],
                            metadatas=[{"url": url}],
                            ids=[url],
                        )

                    # Show appropriate success message
                    num_chunks = len(chunks) if chunks else 1
                    chunk_info = f" ({num_chunks} chunks)" if chunks else ""

                    if has_parsed:
                        st.success(
                            f"✅ Document loaded from parsed cache{chunk_info} "
                            "(no API calls)!"
                        )
                    elif has_original:
                        st.success(
                            f"✅ Document processed from cached original{chunk_info}!"
                        )
                    else:
                        st.success(
                            f"✅ Document downloaded, processed and cached{chunk_info}!"
                        )

with st.container(border=True):
    st.markdown("### Indexed Documents")
    st.markdown(f"Total items indexed: {collection.count()}")

    collection_data = collection.get()

    documents = collection_data["documents"]
    ids = collection_data["ids"]
    metadatas = collection_data.get("metadatas", [])
    enconding = tiktoken.encoding_for_model("gpt-4")

    # Group chunks by URL
    url_groups = {}
    for document, doc_id, metadata in zip(
        documents, ids, metadatas or [{} for _ in ids], strict=False
    ):
        url = metadata.get("url", doc_id.split("#")[0] if "#" in doc_id else doc_id)
        if url not in url_groups:
            url_groups[url] = []
        url_groups[url].append(
            {
                "document": document,
                "id": doc_id,
                "metadata": metadata,
                "tokens": len(enconding.encode(document)),
            }
        )

    # Display by URL
    for url, items in url_groups.items():
        total_tokens = sum(item["tokens"] for item in items)
        num_chunks = len([item for item in items if "#chunk_" in item["id"]])

        # Check if document is in cache
        cache_status = "📁 Cached" if cache.exists(url) else "☁️ Not cached"

        if num_chunks > 0:
            display_text = (
                f"Tokens: {total_tokens}, Chunks: {num_chunks}, "
                f"URL: {url} | {cache_status}"
            )
        else:
            display_text = f"Tokens: {total_tokens}, URL: {url} | {cache_status}"

        with st.expander(display_text, expanded=False):
            # Action buttons
            col1, col2, col3 = st.columns([2, 1, 1])

            with col2:
                if st.button("🔄 Re-index", key=f"reindex_{url}"):
                    # Delete existing entries from ChromaDB
                    existing_ids = [item["id"] for item in items]
                    collection.delete(ids=existing_ids)

                    # Check if document is in cache
                    if cache.has_parsed(url):
                        with st.spinner("Re-indexing from cache..."):
                            document = Document(
                                url,
                                client=OpenAI(api_key=st.secrets["openai_api_key"]),
                                llama_parse=LlamaParse(
                                    api_key=st.secrets["llama_cloud_api_key"],
                                    language="pt",
                                ),
                                cache=cache,
                            )

                            # Get chunks from cache
                            chunks = document.chunks()

                            if chunks:
                                # Re-index chunks
                                documents = []
                                metadatas = []
                                ids = []

                                for chunk in chunks:
                                    documents.append(chunk.content)
                                    chunk_metadata = {
                                        "url": url,
                                        "chunk_index": chunk.index,
                                        "total_chunks": chunk.metadata.get(
                                            "total_chunks", len(chunks)
                                        ),
                                        "start_char": chunk.start_char,
                                        "end_char": chunk.end_char,
                                    }
                                    metadatas.append(chunk_metadata)
                                    ids.append(f"{url}#chunk_{chunk.index}")

                                collection.add(
                                    documents=documents,
                                    metadatas=metadatas,
                                    ids=ids,
                                )
                                st.success(
                                    f"✅ Re-indexed {len(chunks)} chunks from cache!"
                                )
                            else:
                                # Re-index full document
                                markdown_content = document.markdown()
                                collection.add(
                                    documents=[markdown_content],
                                    metadatas=[{"url": url}],
                                    ids=[url],
                                )
                                st.success("✅ Re-indexed document from cache!")
                            st.rerun()
                    else:
                        st.error(
                            "❌ Document not found in cache. Please index it again."
                        )

            with col3:
                if st.button("🗑️ Remove", key=f"remove_{url}"):
                    # Delete from ChromaDB
                    existing_ids = [item["id"] for item in items]
                    collection.delete(ids=existing_ids)
                    st.success("✅ Document removed from index!")
                    st.rerun()

            # Show content
            if num_chunks > 0:
                for item in items:
                    chunk_idx = item["metadata"].get("chunk_index", "?")
                    st.markdown(f"**Chunk {chunk_idx}** ({item['tokens']} tokens)")
                    st.write(item["document"])
                    st.divider()
            else:
                st.write(items[0]["document"])

# Cache statistics section
with st.container(border=True):
    st.markdown("### Cache Management")
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

    # Sync cache with ChromaDB
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔍 Find Orphaned Cache", use_container_width=True):
            # Get all cached documents
            cached_docs = cache.list_cached_documents()
            cached_urls = {doc.get("url") for doc in cached_docs if doc.get("url")}

            # Get all indexed URLs from ChromaDB
            all_indexed = collection.get()
            indexed_urls = set()
            for metadata in all_indexed.get("metadatas", []):
                if metadata and "url" in metadata:
                    indexed_urls.add(metadata["url"])

            # Find orphaned cache entries
            orphaned_urls = cached_urls - indexed_urls

            if orphaned_urls:
                st.warning(f"Found {len(orphaned_urls)} orphaned cache entries:")
                for url in orphaned_urls:
                    st.write(f"- {url}")

                if st.button("🗑️ Clean Orphaned Cache", key="clean_orphaned"):
                    for url in orphaned_urls:
                        cache.clear_cache(url)
                    st.success(
                        f"✅ Cleaned {len(orphaned_urls)} orphaned cache entries!"
                    )
                    st.rerun()
            else:
                st.success("✅ No orphaned cache entries found!")

    with col2:
        if st.button(
            "🧹 Clear All Cache", use_container_width=True, type="secondary"
        ) and st.checkbox("I understand this will delete all cached documents"):
            # Clear all cache
            import shutil

            if cache.cache_dir.exists():
                shutil.rmtree(cache.cache_dir)
                cache.cache_dir.mkdir(parents=True, exist_ok=True)
            st.success("✅ All cache cleared!")
            st.rerun()
