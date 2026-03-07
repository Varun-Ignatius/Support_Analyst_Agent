"""
Run the support analyst multi-agent system.

Usage (from project root):
  set OPENAI_API_KEY=your_key
  python run.py

Or with a specific incident description:
  python run.py "Service X returning 502; started 10 minutes ago."
"""
import sys
from pathlib import Path

# Ensure project root is on path when running as script
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from autogen import GroupChat, GroupChatManager, UserProxyAgent

from config.llm_config import get_llm_config
from agents import (
    create_app_analyst,
    create_database_analyst,
    create_deployment_analyst,
    create_incident_analyst,
    create_lead_engineer,
    create_os_analyst,
    create_web_server_analyst,
)


def is_termination_msg(content) -> bool:
    """Consider the chat done when the lead_engineer says TERMINATE or document is complete."""
    if not content or not isinstance(content, dict):
        return False
    text = content.get("content") or ""
    return "TERMINATE" in text.upper()


def main():
    llm_config = get_llm_config()

    # All participating agents
    incident_analyst = create_incident_analyst(llm_config)
    app_analyst = create_app_analyst(llm_config)
    os_analyst = create_os_analyst(llm_config)
    web_server_analyst = create_web_server_analyst(llm_config)
    deployment_analyst = create_deployment_analyst(llm_config)
    database_analyst = create_database_analyst(llm_config)
    lead_engineer = create_lead_engineer(llm_config)

    support_agents = [
        incident_analyst,
        app_analyst,
        os_analyst,
        web_server_analyst,
        deployment_analyst,
        database_analyst,
        lead_engineer,
    ]

    # User proxy to start the conversation (no code execution, no human input)
    user_proxy = UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        code_execution_config=False,
        is_termination_msg=is_termination_msg,
    )

    group_chat = GroupChat(
        agents=[user_proxy] + support_agents,
        messages=[],
        max_round=20,
        speaker_selection_method="auto",
    )

    manager = GroupChatManager(
        groupchat=group_chat,
        llm_config=llm_config,
        code_execution_config=False,
        is_termination_msg=is_termination_msg,
    )

    # Default incident message if none provided
    incident_msg = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Incident: Web API returning 5xx errors. Please triage and have relevant analysts "
        "analyze logs (you may simulate findings), then have the lead engineer produce an incident document."
    )

    print("Starting support analyst group chat. Message:", incident_msg[:80], "...")
    print("-" * 60)

    user_proxy.initiate_chat(manager, message=incident_msg)

    print("-" * 60)
    print("Group chat finished.")


if __name__ == "__main__":
    main()
