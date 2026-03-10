"""LLM configuration for AutoGen agents. Load from environment (e.g. OPENAI_API_KEY)."""
import os

from dotenv import load_dotenv

load_dotenv()


def get_llm_config():
    """Build LLM config dict for AutoGen. Customize model and API key source as needed."""
    return {
        "config_list": [
            {
                "model": os.environ.get("AUTOGEN_MODEL", "llama3.2"),
                "base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                "api_key": "ollama",
                "api_type": "openai",
            }
        ],
        "temperature": 0,
        "timeout": 300,
    }
