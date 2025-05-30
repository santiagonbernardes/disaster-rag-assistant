import uuid

import streamlit as st
from langfuse.decorators import langfuse_context, observe
from langfuse.openai import OpenAI

PROFILE_OPTIONS = {"victim": "Vítima", "resident": "Residente", "family": "Familiar"}


@st.cache_resource
def client():
    return OpenAI(api_key=st.secrets["openai_api_key"])


def format_profile_options(option):
    return PROFILE_OPTIONS[option]


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

        if st.form_submit_button("Iniciar o chat") and not select_box:
            st.error("Por favor, selecione um perfil antes de continuar.")


def render_chat_history():
    previous_response_id = st.session_state.previous_response_id
    if previous_response_id is None:
        return

    all_messages = (
        client().responses.input_items.list(previous_response_id, order="asc").data
    )

    for message in all_messages:
        with st.chat_message(message.role):
            st.markdown(message.content[0].text)

    with st.chat_message("assistant"):
        st.markdown(st.session_state.last_response)


@observe
def get_an_response(user_prompt):
    langfuse_context.update_current_observation(session_id=st.session_state.session_id)

    return client().responses.create(
        model="gpt-4.1-nano",
        input=user_prompt,
        instructions="Você é um assistente simpático e suscinto.",
        previous_response_id=st.session_state.previous_response_id,
    )


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


    render_chat_history()

    if prompt := st.chat_input("Type a message"):
        with st.chat_message("user"):
            st.markdown(prompt)

        response = get_an_response(prompt)

        st.session_state.last_response = response.output_text
        st.session_state.previous_response_id = response.id
        st.rerun()
