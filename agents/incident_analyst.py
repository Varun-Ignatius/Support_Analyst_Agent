"""Incident analysis agent: triages incidents and coordinates initial assessment."""
from autogen import AssistantAgent


def create_incident_analyst(llm_config: dict) -> AssistantAgent:
    """Create the incident analysis agent."""
    return AssistantAgent(
        name="incident_analyst",
        system_message="""You are an incident analyst. You triage incidents, summarize symptoms and impact.
Output a brief incident summary and provide a list of relevant search keywords for the log_analyzer to query logs with.
CRITICAL: Keywords must be SHORT and PARTIAL — single words or numbers only. Do NOT use multi-word phrases.
Each keyword is matched with ILIKE '%keyword%' so partial matches work, meaning short words are more effective.
✅ CORRECT examples: 503, order, payment, timeout, error, db, auth, checkout, FAILED, traceId
❌ WRONG examples: "Order Failed", "503 Response", "Service Error", "Checkout Failure"
Provide 5-8 short keywords. Also include the exact incident timestamp so the log_analyzer can set the correct time range.
You are not responsible for taking any other actions. Inform chat_manager to pass on information to log_analyzer. Do not respond more than 3 times""",
        llm_config=llm_config,
        description="Triages incidents and provides search keywords for the log analyzer.",
    )
