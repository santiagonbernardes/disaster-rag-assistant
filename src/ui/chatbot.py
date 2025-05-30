import streamlit as st
from openai import OpenAI


def get_openai_client():
    return OpenAI(api_key=st.secrets["openai_api_key"])


def render_chat_history(client):
    previous_response_id = st.session_state.previous_response_id
    if previous_response_id is None:
        return

    all_messages = client.responses.input_items.list(
        previous_response_id, order="asc"
    ).data

    for message in all_messages:
        with st.chat_message(message.role):
            st.markdown(message.content[0].text)

    with st.chat_message("assistant"):
        st.markdown(st.session_state.last_response)


def main():
    st.title("Simple bot")
    client = get_openai_client()

    if "previous_response_id" not in st.session_state:
        st.session_state.previous_response_id = None
    if "last_response" not in st.session_state:
        st.session_state.last_response = None

    render_chat_history(client)

    if prompt := st.chat_input("Type a message"):
        with st.chat_message("user"):
            st.markdown(prompt)

        response = client.responses.create(
            model="gpt-4.1-nano",
            input=prompt,
            instructions="ALWAYS RETURN 'Não sei', regardless of the input.",
            previous_response_id=st.session_state.previous_response_id,
        )

        st.session_state.last_response = response.output_text
        st.session_state.previous_response_id = response.id
        st.rerun()
