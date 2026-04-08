#!/usr/bin/env python3
"""Track prioritization decisions and detect patterns over time.

Usage:
    # Log a prioritization decision
    python prioritization_history.py log --epic AAP-123 --reason "customer-demo" --note "Demo on Friday"

    # Show recent history
    python prioritization_history.py show --limit 20

    # Detect patterns
    python prioritization_history.py patterns

    # Find frequently deprioritized epics
    python prioritization_history.py stale

The history is stored in ~/.backlog-prioritization-history.json
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

HISTORY_FILE = Path.home() / ".backlog-prioritization-history.json"

REASON_TYPES = [
    "customer-commitment",
    "technical-dependency",
    "sprint-deadline",
    "blocker",
    "executive-request",
    "other",
]


def load_history() -> list[dict[str, Any]]:
    """Load prioritization history from file."""
    if not HISTORY_FILE.exists():
        return []
    with open(HISTORY_FILE) as f:
        return json.load(f)


def save_history(history: list[dict[str, Any]]) -> None:
    """Save prioritization history to file."""
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def log_decision(epic: str, reason: str, note: str | None = None, project: str | None = None) -> None:
    """Log a prioritization decision."""
    history = load_history()

    entry = {
        "timestamp": datetime.now().isoformat(),
        "epic": epic,
        "reason": reason,
        "note": note,
        "project": project or epic.split("-")[0],
    }

    history.append(entry)
    save_history(history)

    print(f"Logged: {epic} prioritized for {reason}")
    if note:
        print(f"  Note: {note}")


def show_history(limit: int = 20, project: str | None = None) -> None:
    """Show recent prioritization history."""
    history = load_history()

    if project:
        history = [h for h in history if h.get("project") == project]

    if not history:
        print("No prioritization history found.")
        return

    # Show most recent first
    history = history[-limit:][::-1]

    print(f"Recent prioritization decisions ({len(history)} shown):\n")
    print("| Date | Epic | Reason | Note |")
    print("|------|------|--------|------|")

    for entry in history:
        ts = entry.get("timestamp", "")[:10]
        epic = entry.get("epic", "")
        reason = entry.get("reason", "")
        note = entry.get("note", "") or "-"
        if len(note) > 40:
            note = note[:37] + "..."
        print(f"| {ts} | {epic} | {reason} | {note} |")


def detect_patterns() -> None:
    """Detect patterns in prioritization history."""
    history = load_history()

    if len(history) < 5:
        print("Not enough history for pattern detection (need at least 5 entries).")
        return

    # Count reasons
    reason_counts = Counter(h.get("reason") for h in history)

    # Count projects
    project_counts = Counter(h.get("project") for h in history)

    # Find repeated epics
    epic_counts = Counter(h.get("epic") for h in history)
    repeated = {k: v for k, v in epic_counts.items() if v > 1}

    print("## Prioritization Patterns\n")

    print("### By Reason")
    print("| Reason | Count | % |")
    print("|--------|-------|---|")
    total = len(history)
    for reason, count in reason_counts.most_common():
        pct = round(count / total * 100)
        print(f"| {reason} | {count} | {pct}% |")

    print("\n### By Project")
    print("| Project | Count |")
    print("|---------|-------|")
    for project, count in project_counts.most_common():
        print(f"| {project} | {count} |")

    if repeated:
        print("\n### Frequently Prioritized Epics")
        print("| Epic | Times Prioritized |")
        print("|------|-------------------|")
        for epic, count in sorted(repeated.items(), key=lambda x: -x[1]):
            print(f"| {epic} | {count} |")

    # Suggestions based on patterns
    print("\n### Insights")
    top_reason = reason_counts.most_common(1)[0] if reason_counts else None
    if top_reason and top_reason[1] >= 3:
        reason, count = top_reason
        print(f"- You've prioritized for '{reason}' {count} times. Consider a recurring process for this.")

    if repeated:
        most_repeated = max(repeated.items(), key=lambda x: x[1])
        if most_repeated[1] >= 3:
            print(f"- {most_repeated[0]} has been prioritized {most_repeated[1]} times. Is it blocked or underfunded?")


def find_stale() -> None:
    """Find epics that were deprioritized or never completed."""
    history = load_history()

    if not history:
        print("No prioritization history found.")
        return

    # Count prioritizations per epic
    epic_counts = Counter(h.get("epic") for h in history)

    # Find epics prioritized multiple times (might be stuck)
    stuck = {k: v for k, v in epic_counts.items() if v >= 2}

    if not stuck:
        print("No potentially stale epics found.")
        return

    print("## Potentially Stale Epics\n")
    print("These epics have been prioritized multiple times, which may indicate they are stuck:\n")
    print("| Epic | Times Prioritized | Last Prioritized |")
    print("|------|-------------------|------------------|")

    for epic, count in sorted(stuck.items(), key=lambda x: -x[1]):
        # Find last prioritization date
        last = [h for h in history if h.get("epic") == epic][-1]
        last_date = last.get("timestamp", "")[:10]
        print(f"| {epic} | {count} | {last_date} |")

    print("\nConsider: archiving, re-scoping, or adding resources to these epics.")


def main():
    parser = argparse.ArgumentParser(description="Track prioritization decisions and patterns")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Log command
    log_parser = subparsers.add_parser("log", help="Log a prioritization decision")
    log_parser.add_argument("--epic", "-e", required=True, help="Epic key (e.g., AAP-123)")
    log_parser.add_argument(
        "--reason",
        "-r",
        required=True,
        choices=REASON_TYPES,
        help="Reason for prioritization",
    )
    log_parser.add_argument("--note", "-n", help="Additional context")
    log_parser.add_argument("--project", "-p", help="Project key (default: extracted from epic)")

    # Show command
    show_parser = subparsers.add_parser("show", help="Show recent history")
    show_parser.add_argument("--limit", "-l", type=int, default=20, help="Number of entries to show")
    show_parser.add_argument("--project", "-p", help="Filter by project")

    # Patterns command
    subparsers.add_parser("patterns", help="Detect patterns in history")

    # Stale command
    subparsers.add_parser("stale", help="Find potentially stale epics")

    args = parser.parse_args()

    if args.command == "log":
        log_decision(args.epic, args.reason, args.note, args.project)
    elif args.command == "show":
        show_history(args.limit, args.project)
    elif args.command == "patterns":
        detect_patterns()
    elif args.command == "stale":
        find_stale()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
