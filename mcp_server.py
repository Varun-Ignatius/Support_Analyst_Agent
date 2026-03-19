"""
mcp_server.py — HTTP server exposing the Support Analyst agent as an MCP-compatible tool.

Works with Python 3.9+ (no fastmcp/mcp SDK required).

Exposes two integration surfaces:

1. MCP JSON-RPC endpoint (POST /mcp)
   - Compatible with MCP clients (Claude Desktop via HTTP, custom Slack bots)
   - Supports: initialize, tools/list, tools/call

2. Slack Webhook endpoint (POST /slack/events)
   - Accepts Slack Events API payloads
   - Triggers analysis when a message is posted in a monitored channel
   - Replies back to Slack via the response_url or Web API

Usage:
    python mcp_server.py          # Default: http://0.0.0.0:8000
    python mcp_server.py --port 9000

Environment variables (set in .env):
    MCP_HOST            Host to bind to (default: 0.0.0.0)
    MCP_PORT            Port to listen on (default: 8000)
    SLACK_BOT_TOKEN     Slack Bot OAuth token (xoxb-...) for posting results back
    SLACK_SIGNING_SECRET  Slack signing secret for request verification
"""
import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import threading
from pathlib import Path

from flask import Flask, jsonify, request, Response
from dotenv import load_dotenv

# Ensure project root is importable
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

load_dotenv()

# Lazy import so the server starts fast; agents are loaded on first call
_start_analysis = None

def get_start_analysis():
    global _start_analysis
    if _start_analysis is None:
        from run import start_analysis
        _start_analysis = start_analysis
    return _start_analysis


app = Flask(__name__)

# ---------------------------------------------------------------------------
# MCP Tool definitions (exposed via tools/list)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "analyze_incident",
        "description": (
            "Trigger the support analyst multi-agent pipeline for a given incident. "
            "Runs log analysis via ChromaDB and returns a root-cause incident report."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "incident_message": {
                    "type": "string",
                    "description": (
                        "Plain-text or JSON description of the incident. "
                        "JSON fields: number, category, short_description, "
                        "description, opened_at, severity, assignment_group."
                    ),
                }
            },
            "required": ["incident_message"],
        },
    },
    {
        "name": "search_logs",
        "description": "Search the Better Stack Logtail database for specific keywords and filter by timestamp.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query.",
                },
                "since": {
                    "type": "string",
                    "description": "Start time in format YYYY-MM-DD HH:MM.",
                },
                "until": {
                    "type": "string",
                    "description": "End time in format YYYY-MM-DD HH:MM.",
                },
                "file_name": {
                    "type": "string",
                    "description": "Optional file name to filter by, based on the layer.",
                },
                "n": {
                    "type": "integer",
                    "description": "Number of results. Default is 10.",
                    "default": 10
                }
            },
            "required": ["query"],
        },
    }
]


# ---------------------------------------------------------------------------
# MCP JSON-RPC endpoint  (POST /mcp)
# ---------------------------------------------------------------------------

@app.route("/mcp", methods=["POST"])
def mcp_handler():
    """Handle MCP JSON-RPC 2.0 requests."""
    body = request.get_json(force=True)
    method = body.get("method", "")
    req_id = body.get("id")

    def ok(result):
        return jsonify({"jsonrpc": "2.0", "id": req_id, "result": result})

    def err(code, message):
        return jsonify({"jsonrpc": "2.0", "id": req_id,
                        "error": {"code": code, "message": message}}), 400

    if method == "initialize":
        return ok({
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "support-analyst-agent", "version": "1.0.0"},
        })

    if method == "tools/list":
        return ok({"tools": TOOLS})

    if method == "tools/call":
        params = body.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "analyze_incident":
            incident_message = arguments.get("incident_message", "")
            if not incident_message:
                return err(-32602, "Missing required argument: incident_message")

            try:
                result = get_start_analysis()(incident_message)
                return ok({
                    "content": [{"type": "text", "text": result}],
                    "isError": False,
                })
            except Exception as exc:
                return ok({
                    "content": [{"type": "text", "text": f"Error: {exc}"}],
                    "isError": True,
                })

        elif tool_name == "search_logs":
            query = arguments.get("query", "")
            since = arguments.get("since")
            until = arguments.get("until")
            file_name = arguments.get("file_name")
            n = arguments.get("n", 10)

            if not query:
                return err(-32602, "Missing required argument: query")

            try:
                # We reuse the search_logs function from run.py since it nicely captures query.py output
                from run import search_logs as do_search_logs
                result = do_search_logs(query, since, until, file_name, n)
                return ok({
                    "content": [{"type": "text", "text": result}],
                    "isError": False,
                })
            except Exception as exc:
                return ok({
                    "content": [{"type": "text", "text": f"Error using search_logs: {exc}"}],
                    "isError": True,
                })

        else:
            return err(-32601, f"Unknown tool: {tool_name}")

    # Notifications (no response needed)
    if method.startswith("notifications/"):
        return Response(status=204)

    return err(-32601, f"Method not found: {method}")


# ---------------------------------------------------------------------------
# Slack Events API endpoint  (POST /slack/events)
# ---------------------------------------------------------------------------

def _verify_slack_signature(req) -> bool:
    """Verify the request is genuinely from Slack."""
    signing_secret = os.environ.get("SLACK_SIGNING_SECRET", "")
    if not signing_secret:
        # Skip verification if secret not configured (dev mode)
        return True

    timestamp = req.headers.get("X-Slack-Request-Timestamp", "")
    if abs(time.time() - float(timestamp)) > 60 * 5:
        return False  # Replay attack guard

    sig_basestring = f"v0:{timestamp}:{req.get_data(as_text=True)}"
    computed = "v0=" + hmac.new(
        signing_secret.encode(), sig_basestring.encode(), hashlib.sha256
    ).hexdigest()
    slack_sig = req.headers.get("X-Slack-Signature", "")
    return hmac.compare_digest(computed, slack_sig)


def _post_to_slack(channel: str, text: str):
    """Post a message back to Slack using the Bot token."""
    import urllib.request
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        print("[slack] SLACK_BOT_TOKEN not set — cannot post reply.", file=sys.stderr)
        return
    payload = json.dumps({"channel": channel, "text": text}).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read())
        if not body.get("ok"):
            print(f"[slack] Post failed: {body.get('error')}", file=sys.stderr)


@app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handle incoming Slack Events API payloads."""
    if not _verify_slack_signature(request):
        return jsonify({"error": "Invalid signature"}), 403

    body = request.get_json(force=True)

    # Slack URL verification challenge
    if body.get("type") == "url_verification":
        return jsonify({"challenge": body["challenge"]})

    event = body.get("event", {})
    event_type = event.get("type")

    # Only handle direct messages or app_mentions with text
    if event_type in ("message", "app_mention") and "bot_id" not in event:
        incident_message = event.get("text", "").strip()
        channel = event.get("channel", "")

        if incident_message:
            # Run analysis in a background thread so we can ACK Slack quickly
            def run_and_reply():
                try:
                    result = get_start_analysis()(incident_message)
                    _post_to_slack(channel, f"✅ Analysis complete:\n```{result}```")
                except Exception as exc:
                    _post_to_slack(channel, f"❌ Analysis failed: {exc}")

            threading.Thread(target=run_and_reply, daemon=True).start()

    # Slack requires a 200 within 3 seconds
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "server": "support-analyst-agent"})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Support Analyst MCP + Slack Server")
    parser.add_argument("--host", default=os.environ.get("MCP_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MCP_PORT", "8000")))
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    print(f"Starting Support Analyst MCP server on http://{args.host}:{args.port}", file=sys.stderr)
    print("  Endpoints:", file=sys.stderr)
    print(f"    POST http://{args.host}:{args.port}/mcp          — MCP JSON-RPC", file=sys.stderr)
    print(f"    POST http://{args.host}:{args.port}/slack/events  — Slack Events API", file=sys.stderr)
    print(f"    GET  http://{args.host}:{args.port}/health        — Health check", file=sys.stderr)

    app.run(host=args.host, port=args.port, debug=args.debug)
