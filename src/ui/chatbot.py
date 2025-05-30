import streamlit as st


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

        # API call here.
        response = f"Echo: {prompt}"

        with st.chat_message("assistant"):
            st.markdown(response)
