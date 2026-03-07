# Support Analyst Multi-Agent System

Bare-bones multi-agent incident and log analysis system using [AutoGen](https://microsoft.github.io/autogen/).

## Agents

| Agent | Role |
|-------|------|
| **incident_analyst** | Triages incidents and decides which support domains are relevant |
| **app_analyst** | Application logs, stack traces, app-level errors |
| **os_analyst** | OS/system logs, kernel, resource usage |
| **web_server_analyst** | HTTP/access logs, reverse proxy, web server errors |
| **deployment_analyst** | CI/CD, containers, orchestrator, deployment failures |
| **database_analyst** | DB logs, slow queries, connection/schema issues |
| **lead_engineer** | Aggregates analyst findings and produces the incident document |

Conversation is orchestrated by AutoGen’s **GroupChatManager** (speaker selection `auto`).

## Setup

1. **Python 3.10+** recommended.

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API key:**  
   Copy `.env.example` to `.env` and set `OPENAI_API_KEY` (and optionally `AUTOGEN_MODEL`).

## Run

From the project root:

```bash
python run.py
```

With a custom incident description:

```bash
python run.py "Payment service timeouts in prod; started 15 min ago."
```

The group chat runs until `max_round` or until a message contains `TERMINATE` (e.g. when the lead engineer finishes the document).

## Project layout

```
Support Analyst Agents/
├── config/
│   └── llm_config.py      # LLM config from env
├── agents/
│   ├── __init__.py
│   ├── incident_analyst.py
│   ├── support_analysts.py  # app, os, web_server, deployment, database
│   └── lead_engineer.py
├── run.py                 # GroupChat + GroupChatManager entrypoint
├── requirements.txt
├── .env.example
└── README.md
```

## Next steps

- Add **tools** (e.g. read log files, call APIs) and register them with the relevant agents.
- Tighten **speaker transitions** (e.g. FSM / hub-and-spoke so analysts report only to the lead engineer).
- Add **incident context** (attach log snippets or artifacts) before starting the chat.
- Persist the **lead_engineer** output (e.g. write the markdown document to a file).
- Use **human-in-the-loop** (e.g. `human_input_mode="ALWAYS"` on `user_proxy`) for approval steps.
