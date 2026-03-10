"""Incident analysis agent: triages incidents and coordinates initial assessment."""
from autogen import AssistantAgent


def create_incident_analyst(llm_config: dict) -> AssistantAgent:
    """Create the incident analysis agent."""
    return AssistantAgent(
        name="incident_analyst",
        system_message="""You are an incident analyst. You triage incidents, summarize symptoms and impact.
Output a brief incident summary and provide a list of relevant search keywords (e.g., specific error messages, service names, etc.) for the log analyzer. Be concise. Make sure to give exact time stamp as well for precise log querying.
Make sure to include incident category as one of the main keywords.
You are not responsible for taking any other actions. Inform chat_manager to pass on information to log_analyzer. Do not respond more than 3 times""",
        llm_config=llm_config,
        description="Triages incidents and provides search keywords for the log analyzer.",
    )
