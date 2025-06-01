import tomllib
from pathlib import Path

import streamlit as st  # Using ST to manage the secrets for now
from langfuse.decorators import langfuse_context


def get_app_version():
    pyproject_path = Path(__file__).parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)
    return pyproject_data["project"]["version"]


if __name__ == "__main__":
    # This file is the entrypoint of the application.
    # Add important configuration here like integrations,
    # logging, etc.
    env = st.secrets["langfuse_environment"]

    langfuse_context.configure(
        secret_key=st.secrets["langfuse_secret_key"],
        public_key=st.secrets["langfuse_public_key"],
        host=st.secrets["langfuse_host"],
        environment=env,
    )

    st.set_page_config(
        page_title="Disaster Knowledge Chatbot",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    pages = [
        st.Page(
            "src/ui/chatbot.py",
            title="Disaster Knowledge Chatbot",
            icon="🤖",
            default=True,
        )
    ]

    if env == "dev":
        pages.append(
            st.Page(
                "src/ui/settings.py",
                title="Knowledge Management",
                icon="🛠️",
            )
        )

    st.navigation(pages).run()
