import uuid

import chromadb
import streamlit as st
from langfuse.decorators import langfuse_context, observe
from langfuse.openai import OpenAI

PROFILE_OPTIONS = {
    "victim": {"label": "Vítima", "prompt": "victim"},
    "resident": {"label": "Residente", "prompt": "resident"},
    "family": {"label": "Familiar", "prompt": "family"},
}


@st.cache_resource(show_spinner=True)
def client():
    return OpenAI(api_key=st.secrets["openai_api_key"])


@st.cache_resource(show_spinner=True)
def collection():
    chroma = chromadb.PersistentClient(path=".db/chroma")
    return chroma.get_or_create_collection(name="disaster-documents")


def format_profile_options(option):
    return PROFILE_OPTIONS[option]["label"]


def get_prompt(profile):
    prompt_name = PROFILE_OPTIONS[profile]["prompt"]
    return langfuse_context.client_instance.get_prompt(prompt_name)


def prompt_user_for_profile():
    with st.form(key="user_profile_form"):
        st.markdown("### 🚨 Assistente Virtual para Orientação em Desastres Naturais")
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


def get_retrieved_documents(user_prompt):
    documents = retrieve_documents(user_prompt)
    relevant_docs = get_relevant_documents(documents)

    if not relevant_docs:
        return ""

    return "\n".join(
        [f"Documento {i + 1}: {doc}" for i, doc in enumerate(relevant_docs)]
    )


@observe(name="retrieval")
def retrieve_documents(user_prompt):
    return collection().query(query_texts=user_prompt, n_results=2)


@observe(name="retrieval_filtering")
def get_relevant_documents(documents):
    # How chroma measures distances:
    # https://cookbook.chromadb.dev/faq/#distances-and-similarity
    # 0 is identical. As far away from it, the more different the
    # document is from the query.

    SIMILARITY_THRESHOLD = 1.3
    relevant_docs = []
    distances_and_docs = zip(
        documents["distances"][0], documents["documents"][0], strict=True
    )

    for distance, document in distances_and_docs:
        if distance < SIMILARITY_THRESHOLD:
            relevant_docs.append(document)

    return relevant_docs


@observe
def get_an_response(user_prompt):
    langfuse_context.update_current_observation(session_id=st.session_state.session_id)
    prompt_client = st.session_state.prompt

    retrieved_docs = get_retrieved_documents(user_prompt)

    instruction = prompt_client.compile(retrieved_documents=retrieved_docs)[0][
        "content"
    ]

    return client().responses.create(
        model="gpt-4.1-nano",
        input=user_prompt,
        instructions=instruction,
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
    st.title("Simple bot")
    if "user_profile" not in st.session_state:
        prompt_user_for_profile()
        return
    if "previous_response_id" not in st.session_state:
        st.session_state.previous_response_id = None
    if "last_response" not in st.session_state:
        st.session_state.last_response = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid.uuid4().hex
    if "prompt" not in st.session_state:
        st.session_state.prompt = get_prompt(st.session_state.user_profile)

    render_chat()


main()
