"""Incident analysis agent: triages incidents and coordinates initial assessment."""
from autogen import AssistantAgent


def create_incident_analyst(llm_config: dict) -> AssistantAgent:
    """Create the incident analysis agent."""
    return AssistantAgent(
        name="incident_analyst",
        system_message="""You are an incident analyst. You triage incidents, summarize symptoms and impact,
and decide which support domains are relevant (application, OS, web server, deployment, database).
Output a brief incident summary and which analyst(s) should analyze logs next. Be concise.""",
        llm_config=llm_config,
        description="Triages incidents and coordinates which support analysts should analyze logs.",
    )
