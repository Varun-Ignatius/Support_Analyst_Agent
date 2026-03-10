"""
run.py — Support Analyst multi-agent system entrypoint.

Usage (CLI):
  python run.py
  python run.py '{"number": "INC001", "short_description": "Auth failure spike"}'
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
    create_incident_analyst,
    create_log_analyzer,
    create_lead_engineer,
)
import autogen
import io
import contextlib
import query as query_module


def search_logs(query: str, since: str, until: str, file_name: str = None, n: int = 10) -> str:
    """Useful for searching the log database for specific keywords.

    Args:
        query: The search query keywords.
        since: Mandatory start time in format YYYY-MM-DD HH:MM.
        until: Mandatory end time in format YYYY-MM-DD HH:MM.
        file_name: Optional file name to filter by, based on the layer.
        n: Number of results.
    """
    print(f"\\n[vector_search] Delegating to query.py for: '{query}' from {since} to {until} in file: {file_name}")

    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        try:
            query_module.run_query(
                text=query,
                since=since,
                until=until,
                file_name=file_name,
                top=n
            )
        except Exception as e:
            return f"Error executing query: {str(e)}"

    output = f.getvalue()
    if not output.strip():
        return "No results found."
    return output


def is_termination_msg(content) -> bool:
    """Consider the chat done when the lead_engineer says TERMINATE."""
    if not content or not isinstance(content, dict):
        return False
    text = content.get("content") or ""
    return "TERMINATE" in text.upper()


def start_analysis(incident_msg: str) -> str:
    """Run the full multi-agent analysis pipeline for the given incident message.

    This is the primary entry point for triggering the agent group chat. It can be
    called directly from the CLI (via main()), from an MCP tool handler, or from
    any other integration layer (Slack webhook, REST API, etc.).

    Args:
        incident_msg: A JSON or plain-text description of the incident.

    Returns:
        A string summary or path to the generated incident report.
    """
    llm_config = get_llm_config()

    incident_analyst = create_incident_analyst(llm_config)
    log_analyzer = create_log_analyzer(llm_config)
    lead_engineer = create_lead_engineer(llm_config)

    support_agents = [
        incident_analyst,
        log_analyzer,
        lead_engineer,
    ]

    user_proxy = UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        code_execution_config={"use_docker": False, "work_dir": "."},
        is_termination_msg=is_termination_msg,
    )

    autogen.agentchat.register_function(
        search_logs,
        caller=log_analyzer,
        executor=user_proxy,
        name="search_logs",
        description="Search the log database for specific keywords",
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

    print(f"Starting support analyst group chat. Message: {incident_msg[:80]} ...")
    print("-" * 60)

    user_proxy.initiate_chat(manager, message=incident_msg)

    print("-" * 60)
    print("Group chat finished.")

    # Extract the last message from lead_engineer and return its text directly.
    # Strip the trailing TERMINATE word so the Slack reply is clean.
    lead_engineer_msgs = [
        m for m in group_chat.messages
        if m.get("name") == "lead_engineer"
    ]
    if lead_engineer_msgs:
        report_text = lead_engineer_msgs[-1].get("content", "").strip()
        # Remove trailing TERMINATE line if present
        lines = report_text.splitlines()
        if lines and lines[-1].strip().upper() == "TERMINATE":
            lines = lines[:-1]
        report_text = "\n".join(lines).strip()
        return report_text if report_text else "Analysis complete. No report content was generated."

    return "Analysis complete. No report content was generated."


def main():
    """CLI entrypoint."""
    # Default incident message
    default_incident = """{
    "sys_id": "INC0010001",
    "number": "INC0010001",
    "category": "Network",
    "subcategory": "Intrusion Attempt",
    "severity": "1",
    "priority": "1 - Critical",
    "state": "Resolved",
    "impact": "1 - High",
    "urgency": "1 - High",
    "short_description": "Brute Force Login Attack Detected from Suspicious IP",
    "description": "IP 185.220.101.45 (RU) performed 60 requests/min against /api/auth/login exceeding WAF threshold of 10 req/min. AWS WAF RateLimitLoginRule and IP Blocklist triggered. Traffic subsequently blocked and rejected at VPC level.",
    "assignment_group": "Security Operations",
    "assigned_to": "SOC Team",
    "caller_id": "AWS WAF",
    "cmdb_ci": "shopzone-alb-prod",
    "opened_at": "2024-03-15T09:30:01Z",
    "resolved_at": "2024-03-15T09:30:02Z",
    "closed_at": "2024-03-15T09:30:02Z",
    "resolution_notes": "WAF automatically blocked IP 185.220.101.45 via RateLimitLoginRule and AWSManagedRulesCommon. VPC Flow logs confirm REJECT after block."
    }"""

    incident_msg = sys.argv[1] if len(sys.argv) > 1 else default_incident
    result = start_analysis(incident_msg)
    print(result)


if __name__ == "__main__":
    main()
