"""LLM configuration for AutoGen agents. Load from environment (e.g. OPENAI_API_KEY)."""
import os

from dotenv import load_dotenv

load_dotenv()


def get_llm_config():
    """Build LLM config dict for AutoGen. Customize model and API key source as needed."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    return {
        "config_list": [
            {
                "model": os.environ.get("AUTOGEN_MODEL", "gpt-4"),
                "api_key": api_key,
            }
        ],
        "temperature": 0,
        "timeout": 300,
    }
