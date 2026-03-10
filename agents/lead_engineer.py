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
2. Output the report directly in this conversation using markdown structure:
   title, executive summary, timeline, findings, root cause analysis, and recommended fixes.
CRITICAL CONSTRAINTS:
- The entire report MUST BE under 100 words. Keep it extremely concise.
- Focus strictly on the DETAILS, ROOT CAUSE, and POSSIBLE FIX.
- DO NOT say the incident is fixed or resolved (keep it open and actionable).
- Do NOT write or save any files. Output the report text inline here.
Keep the report clear and use markdown for structure.
IMPORTANT: After outputting the report, append EXACTLY the word TERMINATE on a new line to stop the conversation.""",
        llm_config=llm_config,
        description="Aggregates analyst findings and outputs the final incident report inline.",
    )
