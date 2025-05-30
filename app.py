import tomllib
from pathlib import Path

import streamlit as st  # Using ST to manage the secrets for now
from langfuse.decorators import langfuse_context

from src.ui.chatbot import main


def get_app_version():
    pyproject_path = Path(__file__).parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)
    return pyproject_data["project"]["version"]


if __name__ == "__main__":
    # This file is the entrypoint of the application.
    # Add important configuration here like integrations,
    # logging, etc.

    langfuse_context.configure(
        secret_key=st.secrets["langfuse_secret_key"],
        public_key=st.secrets["langfuse_public_key"],
        host=st.secrets["langfuse_host"],
        environment=st.secrets["langfuse_environment"],
    )
    main()
