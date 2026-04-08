#!/usr/bin/env python3
"""Generate markdown report from Jira epic query results.

Usage:
    python generate_backlog_report.py <json_file> [--project PROJECT]
    cat results.json | python generate_backlog_report.py -

The script expects Jira search results in JSON format with the structure:
{
    "issues": {
        "totalCount": N,
        "nodes": [
            {
                "key": "ACA-123",
                "fields": {
                    "summary": "Epic summary",
                    "status": {"name": "In Progress"},
                    "assignee": {"displayName": "Name"} | null
                },
                "unsprinted_count": 5  // optional, added by caller
            }
        ]
    }
}

If unsprinted_count is provided, the report flags In Progress epics with
unsprinted children using ⚠️ to indicate active work needing sprint planning.
"""

import argparse
import json
import sys
from typing import Any


def parse_epic(issue: dict[str, Any]) -> dict[str, Any]:
    """Extract relevant fields from a Jira issue."""
    fields = issue.get("fields", {})
    assignee = fields.get("assignee")

    return {
        "key": issue.get("key", ""),
        "summary": fields.get("summary", ""),
        "status": fields.get("status", {}).get("name", "Unknown"),
        "assignee": assignee.get("displayName", "Unassigned") if assignee else "Unassigned",
        "unsprinted_count": issue.get("unsprinted_count"),
    }


def generate_markdown_table(epics: list[dict[str, Any]], project: str | None = None) -> str:
    """Generate a markdown table from parsed epics."""
    if not epics:
        return "No epics found matching the query.\n"

    # Check if any epic has unsprinted count data
    has_unsprinted = any(epic.get("unsprinted_count") is not None for epic in epics)

    lines = []

    # Header
    header = f"## {project} Project ({len(epics)} epics)\n" if project else f"## Epics ({len(epics)} total)\n"
    lines.append(header)

    if has_unsprinted:
        lines.append("| # | Epic | Summary | Status | Unsprinted | Assignee |")
        lines.append("|---|------|---------|--------|------------|----------|")
    else:
        lines.append("| # | Epic | Summary | Status | Assignee |")
        lines.append("|---|------|---------|--------|----------|")

    # Rows
    in_progress_flagged = []
    unassigned_epics = []
    for i, epic in enumerate(epics, 1):
        summary = epic["summary"]
        # Truncate long summaries
        if len(summary) > 60:
            summary = summary[:57] + "..."

        # Track unassigned epics
        is_unassigned = epic["assignee"] == "Unassigned"
        if is_unassigned:
            unassigned_epics.append(epic["key"])

        if has_unsprinted:
            unsprinted = epic.get("unsprinted_count", 0) or 0
            # Flag In Progress epics with unsprinted children
            is_in_progress = epic["status"].lower() == "in progress"
            if is_in_progress and unsprinted > 0:
                unsprinted_str = f"{unsprinted} ⚠️"
                in_progress_flagged.append(epic["key"])
            else:
                unsprinted_str = str(unsprinted)
            lines.append(f"| {i} | {epic['key']} | {summary} | {epic['status']} | {unsprinted_str} | {epic['assignee']} |")
        else:
            lines.append(f"| {i} | {epic['key']} | {summary} | {epic['status']} | {epic['assignee']} |")

    # Add recommendations
    if in_progress_flagged:
        lines.append("")
        lines.append(f"⚠️ {', '.join(in_progress_flagged)}: In Progress with unsprinted children — recommend prioritizing these tickets first.")

    if unassigned_epics:
        lines.append("")
        lines.append(f"📋 {', '.join(unassigned_epics)}: Unassigned — consider assigning an owner.")

    return "\n".join(lines) + "\n"


def generate_report(data: dict[str, Any], project: str | None = None) -> str:
    """Generate the full report from Jira API response."""
    issues = data.get("issues", {})
    nodes = issues.get("nodes", [])

    epics = [parse_epic(issue) for issue in nodes]
    return generate_markdown_table(epics, project)


def main():
    parser = argparse.ArgumentParser(description="Generate backlog report from Jira JSON")
    parser.add_argument("input", help="JSON file path or '-' for stdin")
    parser.add_argument("--project", "-p", help="Project name for the header")
    args = parser.parse_args()

    # Read input
    if args.input == "-":
        data = json.load(sys.stdin)
    else:
        with open(args.input) as f:
            data = json.load(f)

    # Generate and print report
    report = generate_report(data, args.project)
    print(report)


if __name__ == "__main__":
    main()
