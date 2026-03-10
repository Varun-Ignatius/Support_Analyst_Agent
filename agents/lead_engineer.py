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
2. Produce a structured document with: title, executive summary, timeline, findings,
   root cause analysis, and recommended possible fixes.
3. Save the document as a `.md` file in the root project directory.
CRITICAL CONSTRAINTS:
- The entire document MUST BE under 100 words. Keep it extremely concise.
- Focus strictly on the DETAILS, ROOT CAUSE, and POSSIBLE FIX. 
- DO NOT provide details stating that the incident is fixed or resolved (keep it open and actionable).
Keep the document clear and use markdown for structure.
IMPORTANT: Once you have successfully generated and saved the document, output EXACTLY the word TERMINATE to stop the conversation.""",
        llm_config=llm_config,
        description="Aggregates analyst findings and writes the final incident document.",
    )
