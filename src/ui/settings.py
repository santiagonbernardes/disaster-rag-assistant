import chromadb
import streamlit as st
import tiktoken
from langfuse.openai import OpenAI
from llama_cloud_services import LlamaParse

from src.retrieval.document import Document

st.header("Settings")

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
            document = Document(
                url,
                client=OpenAI(api_key=st.secrets["openai_api_key"]),
                llama_parse=LlamaParse(
                    api_key=st.secrets["llama_cloud_api_key"], language="pt"
                ),
            )
            collection.add(
                documents=[document.markdown()],
                metadatas=[{"url": url}],
                ids=[url],
            )
            st.success("Document indexed successfully!")

with st.container(border=True):
    st.markdown("### Indexed Documents")
    st.markdown(f"Total documents indexed: {collection.count()}")

    collection_data = collection.get()

    documents = collection_data["documents"]
    ids = collection_data["ids"]
    enconding = tiktoken.encoding_for_model("gpt-4")
    for document, doc_id in zip(documents, ids, strict=False):
        num_token = len(enconding.encode(document))
        with st.expander(f"Tokens: {num_token}, Url: {doc_id}", expanded=False):
            st.write(document)
