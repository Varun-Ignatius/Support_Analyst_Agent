# Support Analyst Multi-Agent System

Multi-agent incident and log analysis system using [AutoGen](https://microsoft.github.io/autogen/), powered by a local [Ollama](https://ollama.ai/) instance and [ChromaDB](https://www.trychroma.com/).

## Agents

| Agent | Role |
|-------|------|
| **incident_analyst** | Triages incidents, summarizes symptoms, and extracts search keywords. |
| **log_analyzer** | Queries the vector database for relevant logs using keywords and timestamps. |
| **lead_engineer** | Aggregates findings and produces a concise incident report (root cause and fixes). |

Conversation is orchestrated by AutoGen’s **GroupChatManager**.

## Setup

1. **Python 3.10+** recommended.

2. **Install Ollama:**
   - Download from [ollama.ai](https://ollama.ai/).
   - Pull the required model: `ollama pull llama3.2`.

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   Copy `.env.example` to `.env`. The system defaults to Ollama at `http://localhost:11434/v1`.

## Run

To run the full multi-agent simulation:

```bash
python run.py
```

## Manual Log Querying

You can query the ingested logs directly using `query.py`:

```bash
# Keyword search
python query.py "auth failure"

# Filtered search
python query.py --severity ERROR --since "2024-03-15 09:00"

# List all (requires optional positional arg support)
python query.py
```

## Project layout

```
Support_Analyst_Agent/
├── agents/            # Multi-agent definitions
├── config/            # LLM configuration (Ollama/OpenAI)
├── chroma_db/         # Local vector database storage
├── vectordb.py        # ChromaDB interface logic
├── query.py           # CLI tool for log querying
├── run.py             # Main entrypoint
├── requirements.txt
└── README.md
```
