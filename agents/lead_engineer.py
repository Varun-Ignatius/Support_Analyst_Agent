"""Lead engineer agent: aggregates analyst findings and produces the incident document."""
from autogen import AssistantAgent


def create_lead_engineer(llm_config: dict) -> AssistantAgent:
    """Create the lead engineer agent that synthesizes analyses into a document."""
    return AssistantAgent(
        name="lead_engineer",
        system_message="""You are the lead engineer. You receive analysis from support analysts
(application, OS, web server, deployment, database) and from the incident analyst.
Your job is to:
1. Summarize all findings into a single incident report.
2. Produce a structured document with: title, executive summary, timeline, findings by domain,
   root cause analysis, recommendations, and next steps.
Keep the document clear and actionable. Use markdown for structure.""",
        llm_config=llm_config,
        description="Aggregates analyst findings and writes the final incident document.",
    )
