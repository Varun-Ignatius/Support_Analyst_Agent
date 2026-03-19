"""
query.py — Search logs from Better Stack Logtail using the Query API.

Usage:
    python query.py "error message"
    python query.py "auth failure" --severity ERROR CRITICAL
    python query.py "timeout" --file application.log
    python query.py "slow response" --service payment-svc
    python query.py "disk full" --since "2024-01-15 14:00" --until "2024-01-15 16:00"
    python query.py "errors" --top 20
"""
import argparse
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

LOGTAIL_API_TOKEN = os.getenv("LOGTAIL_API_TOKEN")
QUERY_URL = "https://eu-fsn-3-connect.betterstackdata.com"

def run_query(
    text: str = "",
    top: int = 10,
    severity: list = None,
    service: str = None,
    file_name: str = None,
    since: str = None,
    until: str = None,
):
    if not LOGTAIL_API_TOKEN or LOGTAIL_API_TOKEN == "your_logtail_api_token_here":
        print("Error: LOGTAIL_API_TOKEN is not set in .env. Please set it to query Logtail.")
        return

    # Construct the SQL query
    sql = "SELECT dt, level, message, file, service FROM logs WHERE 1=1"
    
    if text:
        safe_text = text.replace("'", "''")
        sql += f" AND message ILIKE '%{safe_text}%'"
        
    if severity:
        severities = ", ".join(f"'{s}'" for s in severity)
        sql += f" AND level IN ({severities})"
        
    if service:
        safe_service = service.replace("'", "''")
        sql += f" AND service = '{safe_service}'"
        
    if file_name:
        safe_file = file_name.replace("'", "''")
        sql += f" AND file = '{safe_file}'"
        
    if since:
        try:
            since_dt = _parse_dt(since)
            sql += f" AND dt >= '{since_dt.isoformat()}'"
        except ValueError as e:
            print(str(e))
            return
            
    if until:
        try:
            until_dt = _parse_dt(until)
            sql += f" AND dt <= '{until_dt.isoformat()}'"
        except ValueError as e:
            print(str(e))
            return
            
    sql += f" ORDER BY dt DESC LIMIT {top}"
    
    headers = {
        "Authorization": f"Bearer {LOGTAIL_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(QUERY_URL, headers=headers, json={"query": sql})
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error querying Better Stack API: {e}")
        if 'response' in locals() and response.text:
            print(f"API Response: {response.text}")
        return

    # Handle ClickHouse/Logtail response variants
    if isinstance(data, dict) and "data" in data:
        results = data["data"]
    elif isinstance(data, list):
        results = data
    else:
        print(f"Unexpected response format: {data}")
        return

    if not results:
        print("No results found.")
        return

    print(f"\n{len(results)} result(s) for: \"{text}\"\n")
    print("─" * 70)

    for i, r in enumerate(results, 1):
        # Result could be dict or list (if ClickHouse array format)
        if isinstance(r, dict):
            dt = r.get("dt", "?")
            lvl = r.get("level", "?")
            f_name = r.get("file", "?")
            svc = r.get("service", "?")
            msg = r.get("message", "")
        elif isinstance(r, list) and len(r) >= 5:
            dt, lvl, msg, f_name, svc = r[0], r[1], r[2], r[3], r[4]
        else:
            dt, lvl, f_name, svc, msg = "?", "?", "?", "?", str(r)
            
        print(f"[{i}] {lvl:8}  {f_name}  {svc}  {dt}")
        print()
        preview = str(msg)[:400]
        for line in preview.splitlines():
            print(f"    {line}")
        if len(str(msg)) > 400:
            print("    ...")
        print("─" * 70)

def _parse_dt(s: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: '{s}' — use YYYY-MM-DD HH:MM format")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Search logs via Better Stack Logtail")
    ap.add_argument("query",       nargs="?", default="", help="Natural language search query")
    ap.add_argument("--top",       type=int, default=10,  help="Number of results (default: 10)")
    ap.add_argument("--severity",  nargs="+",             help="Filter e.g. ERROR CRITICAL FATAL")
    ap.add_argument("--file",      default=None,          help="Filter by file name e.g. application.log")
    ap.add_argument("--service",   default=None,          help="Filter by service name")
    ap.add_argument("--since",     default=None,          help="Start time YYYY-MM-DD HH:MM")
    ap.add_argument("--until",     default=None,          help="End time  YYYY-MM-DD HH:MM")
    args = ap.parse_args()

    run_query(
        text=args.query,
        top=args.top,
        severity=args.severity,
        file_name=args.file,
        service=args.service,
        since=args.since,
        until=args.until,
    )