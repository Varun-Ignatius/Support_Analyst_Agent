"""Support analyst agents for application, OS, web server, deployment, and database log analysis."""
from autogen import AssistantAgent


def _analyst(name: str, domain: str, focus: str, llm_config: dict) -> AssistantAgent:
    """Factory for support analysts with a common pattern."""
    return AssistantAgent(
        name=name,
        system_message=f"""You are a {domain} support analyst. You analyze logs and metrics for {focus}.
Provide structured findings: relevant log lines, errors, warnings, and a short conclusion.
If the provided context is outside your domain, say so briefly and suggest the right analyst.""",
        llm_config=llm_config,
        description=f"Analyzes {domain} logs and reports findings.",
    )


def create_app_analyst(llm_config: dict) -> AssistantAgent:
    """Application log analyst."""
    return _analyst(
        "app_analyst",
        "application",
        "application logs, stack traces, and app-level errors",
        llm_config,
    )


def create_os_analyst(llm_config: dict) -> AssistantAgent:
    """Operating system log analyst."""
    return _analyst(
        "os_analyst",
        "operating system",
        "system logs, kernel messages, resource usage, and OS-level issues",
        llm_config,
    )


def create_web_server_analyst(llm_config: dict) -> AssistantAgent:
    """Web server log analyst."""
    return _analyst(
        "web_server_analyst",
        "web server",
        "HTTP/access logs, reverse proxy logs, and web server errors",
        llm_config,
    )


def create_deployment_analyst(llm_config: dict) -> AssistantAgent:
    """Deployment and orchestration log analyst."""
    return _analyst(
        "deployment_analyst",
        "deployment",
        "CI/CD, container/orchestrator logs, and deployment failures",
        llm_config,
    )


def create_database_analyst(llm_config: dict) -> AssistantAgent:
    """Database log analyst."""
    return _analyst(
        "database_analyst",
        "database",
        "DB logs, slow queries, connection errors, and schema/query issues",
        llm_config,
    )
