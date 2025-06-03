import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

# Fix for ChromaDB SQLite compatibility on Streamlit Cloud
try:
    import pysqlite3

    sys.modules["sqlite3"] = pysqlite3
except ImportError:
    pass

import chromadb
import streamlit as st
from langfuse.decorators import langfuse_context, observe
from langfuse.openai import OpenAI

PROFILE_OPTIONS = {
    "victim": {"label": "Vítima", "prompt": "victim"},
    "resident": {"label": "Residente", "prompt": "resident"},
    "family": {"label": "Familiar", "prompt": "family"},
}


@dataclass
class ChatMessage:
    """Modelo de dados para mensagens do chat."""
    role: str  # "user" | "assistant"
    content: str  # Conteúdo limpo para exibição ao usuário
    timestamp: datetime
    raw_content: Optional[str] = None  # Conteúdo original com contexto (para debugging)
    retrieval_context: Optional[str] = None  # Para debugging/observabilidade


@st.cache_resource(show_spinner=True)
def client():
    return OpenAI(api_key=st.secrets["openai_api_key"])


@st.cache_resource(show_spinner=True)
def collection():
    chroma = chromadb.PersistentClient(path=".db/chroma")
    return chroma.get_or_create_collection(name="disaster-documents")


# === Utilitários para Gerenciamento de Histórico Local ===

def init_chat_history():
    """Inicializa o histórico do chat no session_state."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history: List[ChatMessage] = []

def add_message_to_history(role: str, content: str, raw_content: Optional[str] = None, retrieval_context: Optional[str] = None):
    """Adiciona uma mensagem ao histórico local."""
    init_chat_history()
    message = ChatMessage(
        role=role,
        content=content,  # Versão limpa para exibição
        timestamp=datetime.now(),
        raw_content=raw_content,  # Versão com contexto para debugging
        retrieval_context=retrieval_context
    )
    st.session_state.chat_history.append(message)

def get_chat_history() -> List[ChatMessage]:
    """Retorna o histórico do chat."""
    init_chat_history()
    return st.session_state.chat_history

def clear_chat_history():
    """Limpa o histórico do chat."""
    st.session_state.chat_history = []

def get_conversation_context() -> str:
    """Retorna o contexto da conversa para o LLM."""
    history = get_chat_history()
    if not history:
        return ""
    
    # Pega as últimas 10 mensagens para contexto
    recent_messages = history[-10:]
    context_parts = []
    
    for msg in recent_messages:
        context_parts.append(f"{msg.role}: {msg.content}")
    
    return "\n".join(context_parts)

def render_local_chat_history():
    """Renderiza o histórico local sem system prompts ou contexto RAG."""
    history = get_chat_history()
    
    for message in history:
        with st.chat_message(message.role):
            st.markdown(message.content)  # Apenas o conteúdo limpo


def format_profile_options(option):
    return PROFILE_OPTIONS[option]["label"]


def get_prompt(profile):
    prompt_name = PROFILE_OPTIONS[profile]["prompt"]
    return langfuse_context.client_instance.get_prompt(prompt_name)


def prompt_user_for_profile():
    with st.form(key="user_profile_form"):
        st.markdown("### Bem-vindo ao Assistente de Desastres Naturais")
        st.markdown(
            "Olá! Sou seu assistente virtual especializado em orientações "
            "para situações de emergência e desastres naturais."
        )

        select_box = st.selectbox(
            "**Para melhor atendê-lo, por favor selecione seu perfil:**",
            options=PROFILE_OPTIONS.keys(),
            placeholder="Selecione seu perfil",
            key="user_profile",
            format_func=format_profile_options,
        )

        if st.form_submit_button("Iniciar o chat"):
            if not select_box:
                st.error("Por favor, selecione um perfil antes de continuar.")
            else:
                st.session_state.user_profile = select_box


def render_chat_history():
    previous_response_id = st.session_state.previous_response_id
    if previous_response_id is None:
        st.empty()
        return

    all_messages = (
        client().responses.input_items.list(previous_response_id, order="asc").data
    )

    for message in all_messages:
        with st.chat_message(message.role):
            st.markdown(message.content[0].text)

    with st.chat_message("assistant"):
        st.markdown(st.session_state.last_response)


@observe(name="document_retrieval_with_metadata")
def get_retrieved_documents(user_prompt):
    # Get user profile-based metadata filter
    metadata_filter = get_profile_based_filter()
    
    # Log filter information for observability
    filter_info = {
        "user_profile": st.session_state.get("user_profile", "none"),
        "filter_applied": metadata_filter is not None,
        "filter_conditions": (
            len(metadata_filter.get("$or", [])) if metadata_filter else 0
        )
    }
    print(f"Retrieval filter info: {filter_info}")
    
    # Retrieve documents with optional filtering
    documents = retrieve_documents(user_prompt, metadata_filter)
    relevant_docs = get_relevant_documents(documents)

    # Log retrieval results
    retrieval_stats = {
        "total_candidates": (
            len(documents.get("ids", [[]])[0]) if documents.get("ids") else 0
        ),
        "relevant_docs_found": len(relevant_docs),
        "filter_effectiveness": (
            len(relevant_docs) / max(len(documents.get("ids", [[]])[0]), 1)
            if documents.get("ids") else 0
        )
    }
    print(f"Retrieval stats: {retrieval_stats}")

    if not relevant_docs:
        return ""

    formatted_docs = []
    for i, doc in enumerate(relevant_docs):
        chunk_info = doc.get("chunk_info", "")
        doc_header = f"Documento {i + 1} - URL: {doc['url']} {chunk_info}"
        doc_content = doc["content"]
        formatted_docs.append(f"{doc_header}\n{doc_content}")

    return "\n\n".join(formatted_docs)


def get_profile_based_filter():
    """
    Generate metadata filter based on user profile.
    
    Returns:
        Dictionary with ChromaDB where conditions or None
    """
    if "user_profile" not in st.session_state:
        return None
    
    user_profile = st.session_state.user_profile
    
    # Profile-based filtering
    profile_filters = {
        "victim": {
            # Victims need immediate response information
            "$or": [
                {"information_type": "response"},
                {"urgency_level": {"$in": ["critical", "high"]}},
                {"target_audience": "victim"},
            ]
        },
        "resident": {
            # Residents need preparation and prevention info
            "$or": [
                {"information_type": {"$in": ["prevention", "preparation"]}},
                {"target_audience": {"$in": ["resident", "victim"]}},
            ]
        },
        "family": {
            # Families need general guidance and contact information
            "$or": [
                {"target_audience": {"$in": ["family", "victim"]}},
                {"has_emergency_contacts": True},
                {"information_type": {"$in": ["response", "recovery"]}},
            ]
        },
    }
    
    return profile_filters.get(user_profile)


@observe(name="retrieval")
def retrieve_documents(user_prompt, metadata_filter=None):
    query_params = {
        "query_texts": user_prompt,
        "n_results": 5  # Increased to get more candidates for filtering
    }
    
    # Add metadata filter if provided
    if metadata_filter:
        query_params["where"] = metadata_filter
    
    return collection().query(**query_params)


@observe(name="retrieval_filtering")
def get_relevant_documents(documents):
    # How chroma measures distances:
    # https://cookbook.chromadb.dev/faq/#distances-and-similarity
    # 0 is identical. As far away from it, the more different the
    # document is from the query.

    SIMILARITY_THRESHOLD = 1.3
    relevant_docs = []

    # Handle metadatas if available
    metadatas = documents.get("metadatas", [[{} for _ in documents["ids"][0]]])

    # Track metadata for observability
    metadata_stats = {
        "total_candidates": (
            len(documents.get("ids", [[]])[0]) if documents.get("ids") else 0
        ),
        "documents_with_metadata": 0,
        "documents_with_confidence": 0,
        "avg_confidence": 0,
        "metadata_fields_found": set()
    }

    documents_data = zip(
        documents["ids"][0],
        documents["distances"][0],
        documents["documents"][0],
        metadatas[0],
        strict=True,
    )

    confidence_scores = []
    
    for doc_id, distance, document, metadata in documents_data:
        # Track metadata statistics
        if metadata:
            metadata_stats["documents_with_metadata"] += 1
            metadata_stats["metadata_fields_found"].update(metadata.keys())
            
            if "confidence_score" in metadata:
                metadata_stats["documents_with_confidence"] += 1
                confidence_scores.append(metadata["confidence_score"])
        
        if distance < SIMILARITY_THRESHOLD:
            # Extract URL from metadata or from doc_id
            url = metadata.get("url", doc_id.split("#")[0] if "#" in doc_id else doc_id)

            doc_info = {"url": url, "content": document}

            # Add chunk info if this is a chunk
            if "#chunk_" in doc_id:
                chunk_idx = metadata.get("chunk_index", doc_id.split("_")[-1])
                total_chunks = metadata.get("total_chunks", "?")
                doc_info["chunk_info"] = f"(Trecho {chunk_idx + 1} de {total_chunks})"

            relevant_docs.append(doc_info)

    # Calculate final statistics
    if confidence_scores:
        metadata_stats["avg_confidence"] = (
            sum(confidence_scores) / len(confidence_scores)
        )
    metadata_stats["metadata_fields_found"] = list(
        metadata_stats["metadata_fields_found"]
    )
    metadata_stats["docs_passed_similarity"] = len(relevant_docs)
    
    print(f"Document filtering stats: {metadata_stats}")

    return relevant_docs


@observe
def get_an_response(user_prompt):
    langfuse_context.update_current_observation(session_id=st.session_state.session_id)
    prompt_client = st.session_state.prompt

    retrieved_docs = get_retrieved_documents(user_prompt)

    compiled_prompt = prompt_client.compile(context=retrieved_docs, question=user_prompt)

    return client().responses.create(
        model=prompt_client.config["model"],
        temperature=prompt_client.config["temperature"],
        input=compiled_prompt,
        previous_response_id=st.session_state.previous_response_id,
        langfuse_prompt=prompt_client,
    )


@st.fragment
def render_chat():
    render_chat_history()
    if prompt := st.chat_input("Type a message"):
        with st.chat_message("user"):
            st.markdown(prompt)

        response = get_an_response(prompt)

        st.session_state.last_response = response.output_text
        st.session_state.previous_response_id = response.id
        st.rerun(scope="fragment")


def main():
    st.title("🚨 Assistente Virtual para Orientação em Desastres Naturais")
    
    if "user_profile" not in st.session_state:
        prompt_user_for_profile()
        return
    
    # Inicialização do session state
    if "previous_response_id" not in st.session_state:
        st.session_state.previous_response_id = None
    if "last_response" not in st.session_state:
        st.session_state.last_response = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid.uuid4().hex
    if "prompt" not in st.session_state:
        st.session_state.prompt = get_prompt(st.session_state.user_profile)
    
    # Inicializar novo sistema de histórico local
    init_chat_history()
    
    render_chat()


main()
