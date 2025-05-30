import chromadb
import streamlit as st

st.header("Settings")

client = chromadb.PersistentClient(path=".db/chroma")
client.create_collection(name="disaster-documents", get_or_create=True)
