import streamlit as st
from openai import OpenAI

def get_openai_client():
    return OpenAI(api_key=st.secrets["openai_api_key"])


def main():
    st.title("Echo Bot")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Type a message"):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        client = get_openai_client()
        response = client.responses.create(
            model="gpt-4.1-nano",
            input=st.session_state.messages,
            instructions="ALWAYS RETURN 'Não sei', regardless of the input.",
        )

        developer_message = response.output_text
        st.session_state.messages.append({"role": "assistant", "content": developer_message})

        with st.chat_message("developer"):
            st.markdown(developer_message)
