import streamlit as st
from langfuse.openai import OpenAI
from langfuse.decorators import observe, langfuse_context
import uuid


@st.cache_resource
def client():
    return OpenAI(api_key=st.secrets["openai_api_key"])


def render_chat_history():
    previous_response_id = st.session_state.previous_response_id
    if previous_response_id is None:
        return

    all_messages = client().responses.input_items.list(
        previous_response_id, order="asc"
    ).data

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
    if "previous_response_id" not in st.session_state:
        st.session_state.previous_response_id = None
    if "last_response" not in st.session_state:
        st.session_state.last_response = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid.uuid4().hex
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = None

    # if not st.session_state.user_profile:
    #     st.session_state.user_profile = prompt_user_for_profile()
    #     return

    render_chat_history()

    if prompt := st.chat_input("Type a message"):
        with st.chat_message("user"):
            st.markdown(prompt)

        response = get_an_response(prompt)

        st.session_state.last_response = response.output_text
        st.session_state.previous_response_id = response.id
        st.rerun()
