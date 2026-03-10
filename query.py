"""
query.py — Search ingested logs from the command line.

Usage:
    python query.py "error message"
    python query.py "auth failure" --severity ERROR CRITICAL
    python query.py "timeout" --file application.log
    python query.py "timeout" --file application.log --severity ERROR CRITICAL FATAL
    python query.py "slow response" --service payment-svc
    python query.py "disk full" --since "2024-01-15 14:00" --until "2024-01-15 16:00"
    python query.py "errors" --top 20
"""
import argparse
from datetime import datetime

import vectordb


def run_query(
    text: str = "",
    top: int = 10,
    severity: list = None,
    service: str = None,
    file_name: str = None,
    since: str = None,
    until: str = None,
):
    since_dt = _parse_dt(since) if since else None
    until_dt = _parse_dt(until) if until else None

    results = vectordb.query(
        text=text,
        n=top,
        severity=severity,
        service=service,
        file_name=file_name,
        since=since_dt,
        until=until_dt,
    )

    if not results:
        print("No results found.")
        return

    print(f"\n{len(results)} result(s) for: \"{text}\"\n")
    print("─" * 70)

    for i, r in enumerate(results, 1):
        m = r["metadata"]
        print(f"[{i}] score={r['score']:.3f}  "
              f"{m.get('severity','?'):8}  "
              f"{m.get('file_name','?')}  "
              f"lines {m.get('line_start')}–{m.get('line_end')}  "
              f"{m.get('timestamp','')[:19]}")
        print()
        preview = r["content"][:400]
        for line in preview.splitlines():
            print(f"    {line}")
        if len(r["content"]) > 400:
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
    ap = argparse.ArgumentParser(description="Search ingested logs")
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