# Support Analyst Multi-Agent System

Multi-agent incident and log analysis system using [AutoGen](https://microsoft.github.io/autogen/), powered by a local [Ollama](https://ollama.ai/) instance and [ChromaDB](https://www.trychroma.com/). Incidents can be triggered from the CLI, an MCP client (e.g. Slack), or any custom integration.

## Agents

| Agent | Role |
|-------|------|
| **incident_analyst** | Triages incidents, summarizes symptoms, and extracts search keywords. |
| **log_analyzer** | Queries the vector database for relevant logs using keywords and timestamps. |
| **lead_engineer** | Aggregates findings and produces a concise incident report (root cause and fixes). |

Conversation is orchestrated by AutoGen's **GroupChatManager**.

## Setup

1. **Python 3.10+** recommended.

2. **Install Ollama** from [ollama.ai](https://ollama.ai/) and pull the model:
   ```bash
   ollama pull llama3.2
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env as needed (Ollama URL, MCP host/port)
   ```

## Run via CLI

```bash
python run.py
# Or pass a custom incident JSON:
python run.py '{"number": "INC001", "short_description": "Auth failure spike"}'
```

## Run as MCP Server (Slack Integration)

The `mcp_server.py` exposes the agent pipeline as an **MCP tool** (`analyze_incident`) that any MCP-compatible client can discover and invoke — including a Slack MCP connector.

```bash
# SSE (HTTP) mode — for networked clients / Slack:
python mcp_server.py

# stdio mode — for Claude Desktop or mcp dev tool:
python mcp_server.py --stdio

# Inspect with the MCP dev inspector:
mcp dev mcp_server.py
```

The server listens at `http://0.0.0.0:8000/sse` by default (configurable via `MCP_HOST` / `MCP_PORT` in `.env`).

### MCP Tool: `analyze_incident`

| Field | Type | Description |
|-------|------|-------------|
| `incident_message` | `string` | Plain text or JSON incident description |

**Returns:** A string confirming completion and the path to the generated `.md` report.

### Slack Integration Flow
```
Slack message / slash command
       │
       ▼
  Slack MCP client (or webhook bridge)
       │
       ▼
  mcp_server.py  →  analyze_incident()
       │
       ▼
  run.py → start_analysis()  →  AutoGen GroupChat
       │
       ▼
  Incident report (.md) saved to project root
```

## Manual Log Querying

```bash
python query.py "auth failure" --severity ERROR --since "2024-03-15 09:00"
python query.py  # no keyword — returns recent results
```

## Project Layout

```
Support_Analyst_Agent/
├── agents/
│   ├── __init__.py
│   ├── incident_analyst.py
│   ├── log_analyzer.py
│   └── lead_engineer.py
├── config/
│   └── llm_config.py       # Ollama / OpenAI LLM config
├── chroma_db/              # Local vector database storage
├── mcp_server.py           # MCP server (Slack / Claude Desktop)
├── run.py                  # CLI entrypoint + start_analysis()
├── vectordb.py             # ChromaDB interface
├── query.py                # CLI log query tool
├── requirements.txt
├── .env.example
└── README.md
```
