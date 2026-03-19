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
import contextlib
import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from datetime import datetime

# Better Stack source details for varun-proj
_BS_SOURCE_ID = 2304104
_BS_TABLE = "t516245.varun_proj"
_BS_S3_COLLECTION = "t516245_varun_proj_s3"   # historical (>30 min old)
_BS_HOT_COLLECTION = "t516245_varun_proj_logs" # recent (<30 min)


def _parse_dt(s: str) -> str:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).isoformat()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: '{s}'")


def _build_sql(keywords: list, since: str, until: str, file_name: str, n: int) -> str:
    """Build a ClickHouse SQL query for Better Stack telemetry.

    All log fields live inside the `raw` JSON column and must be extracted
    with JSONExtract(raw, 'field', 'Nullable(String)').
    Multiple keywords are combined with OR inside a single AND block.
    We use s3Cluster for historical data (the typical case for incident queries).
    """
    where_clauses = ["_row_type = 1"]  # logs only (not spans)

    if keywords:
        keyword_conditions = " OR ".join(
            f"JSONExtract(raw, 'message', 'Nullable(String)') ILIKE '%{kw.strip().replace(chr(39), chr(39)*2)}%'"
            for kw in keywords if kw.strip()
        )
        if keyword_conditions:
            where_clauses.append(f"({keyword_conditions})")

    if file_name:
        safe_f = file_name.replace("'", "''")
        where_clauses.append(
            f"JSONExtract(raw, 'file', 'Nullable(String)') = '{safe_f}'"
        )

    if since:
        where_clauses.append(f"dt >= '{_parse_dt(since)}'")
    if until:
        where_clauses.append(f"dt <= '{_parse_dt(until)}'")

    where = " AND ".join(where_clauses)

    sql = f"""SELECT dt, JSONExtract(raw, 'level', 'Nullable(String)') AS level, JSONExtract(raw, 'message', 'Nullable(String)') AS message FROM s3Cluster(primary, {_BS_S3_COLLECTION}) WHERE {where} ORDER BY dt DESC LIMIT {n}"""
    return sql


def search_logs(query: str, since: str, until: str, file_name: str = None, n: int = 10) -> str:
    """Useful for searching the log database for specific keywords.

    Args:
        query: Comma-separated list of keywords to search for (e.g. "Order Service,503 error,timeout").
               All keywords are combined with OR in a single query.
        since: Mandatory start time in format YYYY-MM-DD HH:MM.
        until: Mandatory end time in format YYYY-MM-DD HH:MM.
        file_name: Optional file name to filter by, based on the layer.
        n: Number of results.
    """
    # Split comma-separated keywords into a list
    keywords = [kw.strip() for kw in query.split(",") if kw.strip()]

    print(f"\\n[search_logs] Querying Better Stack via official MCP server.")
    print(f"[search_logs] Keywords ({len(keywords)}): {keywords}")
    print(f"[search_logs] Time range: {since} to {until} | file_name: {file_name} | limit: {n}")

    api_token = os.environ.get("BETTERSTACK_API_TOKEN") or os.environ.get("LOGTAIL_API_TOKEN")
    if not api_token:
        return "Error: Missing BETTERSTACK_API_TOKEN (or LOGTAIL_API_TOKEN) in .env."

    sql = _build_sql(keywords, since, until, file_name, n)
    print(f"[search_logs] SQL: {sql}")

    async def _run_mcp():
        params = StdioServerParameters(
            command="npx",
            args=[
                "-y", "mcp-remote",
                "https://mcp.betterstack.com",
                "--header", f"Authorization: Bearer {api_token}",
            ],
            env=os.environ.copy(),
        )
        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        "telemetry_query",
                        arguments={
                            "query": sql,
                            "source_id": _BS_SOURCE_ID,
                            "table": _BS_TABLE,
                        },
                    )
                    if result.isError:
                        err_text = "\n".join(getattr(c, "text", str(c)) for c in result.content)
                        return f"Query failed: {err_text}"
                    if not result.content:
                        return "No logs found."
                    return "\n".join(
                        getattr(c, "text", str(c)) for c in result.content
                    ) or "No logs found."
        except Exception as e:
            return f"Error querying Better Stack MCP: {e}"

    return asyncio.run(_run_mcp())



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
