"""
test_betterstack_mcp.py — Interactive test harness for the Better Stack MCP connection.

Usage:
    python test_betterstack_mcp.py              # interactive REPL
    python test_betterstack_mcp.py --list       # list all available tools
    python test_betterstack_mcp.py --sources    # list all log sources
    python test_betterstack_mcp.py --sql "SELECT ..."  # run a raw SQL query

Source details for this project:
    source_id : 2304104
    table     : t516245.varun_proj
    hot (last 30 min) : remote(t516245_varun_proj_logs)
    historical         : s3Cluster(primary, t516245_varun_proj_s3) WHERE _row_type = 1

Quick reference — fields live inside the `raw` JSON column:
    JSONExtract(raw, 'message',  'Nullable(String)') AS message
    JSONExtract(raw, 'level',    'Nullable(String)') AS level
    JSONExtract(raw, 'service',  'Nullable(String)') AS service
    JSONExtract(raw, 'file',     'Nullable(String)') AS file

Example SQL (historical, older than 30 min):
    SELECT dt,
           JSONExtract(raw, 'level',   'Nullable(String)') AS level,
           JSONExtract(raw, 'message', 'Nullable(String)') AS message
    FROM s3Cluster(primary, t516245_varun_proj_s3)
    WHERE _row_type = 1
      AND dt >= '2026-03-18T00:00:00'
      AND dt <= '2026-03-18T23:59:59'
      AND JSONExtract(raw, 'level', 'Nullable(String)') = 'error'
    ORDER BY dt DESC
    LIMIT 10

Example SQL (recent, last 30 min hot storage):
    SELECT dt,
           JSONExtract(raw, 'level',   'Nullable(String)') AS level,
           JSONExtract(raw, 'message', 'Nullable(String)') AS message
    FROM remote(t516245_varun_proj_logs)
    ORDER BY dt DESC
    LIMIT 10
"""

import argparse
import asyncio
import os
import sys
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

SOURCE_ID = 2304104
TABLE = "t516245.varun_proj"

API_TOKEN = os.environ.get("BETTERSTACK_API_TOKEN") or os.environ.get("LOGTAIL_API_TOKEN")
if not API_TOKEN:
    print("ERROR: Set BETTERSTACK_API_TOKEN or LOGTAIL_API_TOKEN in your .env file.")
    sys.exit(1)


def _make_params() -> StdioServerParameters:
    return StdioServerParameters(
        command="npx",
        args=[
            "-y", "mcp-remote",
            "https://mcp.betterstack.com",
            "--header", f"Authorization: Bearer {API_TOKEN}",
        ],
        env=os.environ.copy(),
    )


async def run_query(sql: str) -> str:
    """Execute a raw SQL query against the varun-proj source and return results."""
    async with stdio_client(_make_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "telemetry_query",
                arguments={"query": sql, "source_id": SOURCE_ID, "table": TABLE},
            )
            if result.isError:
                return "ERROR: " + "\n".join(getattr(c, "text", str(c)) for c in result.content)
            return "\n".join(getattr(c, "text", str(c)) for c in result.content) or "(empty result)"


async def list_tools() -> None:
    async with stdio_client(_make_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"\n{'Tool Name':<60} Required args")
            print("─" * 100)
            for t in sorted(tools.tools, key=lambda x: x.name):
                required = t.inputSchema.get("required", [])
                print(f"{t.name:<60} {required}")


async def list_sources() -> None:
    async with stdio_client(_make_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("telemetry_list_sources_tool", arguments={})
            for c in result.content:
                print(getattr(c, "text", str(c)))


async def interactive_repl() -> None:
    """Simple interactive SQL REPL."""
    print("\n━━━ Better Stack MCP Interactive REPL ━━━")
    print(f"Source ID : {SOURCE_ID}")
    print(f"Table     : {TABLE}")
    print("Type a SQL query and press Enter twice to execute.")
    print("Type 'exit' or Ctrl-C to quit.\n")

    async with stdio_client(_make_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Connected to Better Stack MCP server\n")

            while True:
                print("SQL> ", end="", flush=True)
                lines = []
                try:
                    while True:
                        line = input()
                        if line.lower().strip() in ("exit", "quit"):
                            print("Goodbye!")
                            return
                        if line == "" and lines:
                            break
                        lines.append(line)
                except (EOFError, KeyboardInterrupt):
                    print("\nGoodbye!")
                    return

                sql = "\n".join(lines).strip()
                if not sql:
                    continue

                print("\nRunning query...\n")
                result = await session.call_tool(
                    "telemetry_query",
                    arguments={"query": sql, "source_id": SOURCE_ID, "table": TABLE},
                )
                if result.isError:
                    print("ERROR:", "\n".join(getattr(c, "text", str(c)) for c in result.content))
                else:
                    for c in result.content:
                        print(getattr(c, "text", str(c)))
                print()


def main():
    parser = argparse.ArgumentParser(description="Better Stack MCP test harness")
    parser.add_argument("--list",    action="store_true", help="List all available MCP tools")
    parser.add_argument("--sources", action="store_true", help="List all log sources")
    parser.add_argument("--sql",     metavar="QUERY",     help="Run a single SQL query and exit")
    args = parser.parse_args()

    if args.list:
        asyncio.run(list_tools())
    elif args.sources:
        asyncio.run(list_sources())
    elif args.sql:
        result = asyncio.run(run_query(args.sql))
        print(result)
    else:
        asyncio.run(interactive_repl())


if __name__ == "__main__":
    main()
