#!/usr/bin/env python3
"""Parse Jira epic query results preserving backlog rank order.

Usage:
    python parse_epics.py <json_file> [--with-children <children_json>]
    cat results.json | python parse_epics.py -

Examples:
    python parse_epics.py epics.json
    python parse_epics.py epics.json --with-children children.json
"""

import argparse
import json
import sys
from collections import defaultdict


def parse_epics(data: dict) -> list[dict]:
    """Extract epic info preserving backlog order."""
    epics = []
    for node in data.get("issues", {}).get("nodes", []):
        fields = node.get("fields", {})
        assignee = fields.get("assignee")
        epics.append({
            "key": node.get("key"),
            "summary": fields.get("summary", ""),
            "status": fields.get("status", {}).get("name", "Unknown"),
            "assignee": assignee.get("displayName") if assignee else "Unassigned",
        })
    return epics


def parse_children(data: dict) -> dict[str, list[dict]]:
    """Group children by parent epic key, preserving order."""
    grouped = defaultdict(list)
    for node in data.get("issues", {}).get("nodes", []):
        fields = node.get("fields", {})
        parent = fields.get("parent", {})
        parent_key = parent.get("key", "Unknown")
        grouped[parent_key].append({
            "key": node.get("key"),
            "summary": fields.get("summary", ""),
            "status": fields.get("status", {}).get("name", "Unknown"),
        })
    return dict(grouped)


def format_table(epics: list[dict], children: dict[str, list[dict]] | None = None) -> str:
    """Format epics as markdown table preserving backlog order."""
    lines = []

    if children:
        lines.append("| # | Epic | Summary | Unsprinted | Status | Assignee |")
        lines.append("|---|------|---------|------------|--------|----------|")
    else:
        lines.append("| # | Epic | Summary | Status | Assignee |")
        lines.append("|---|------|---------|--------|----------|")

    for i, epic in enumerate(epics, 1):
        key = epic["key"]
        summary = epic["summary"][:55] + "..." if len(epic["summary"]) > 55 else epic["summary"]
        status = epic["status"]
        assignee = epic["assignee"]

        if children:
            count = len(children.get(key, []))
            lines.append(f"| {i} | {key} | {summary} | {count} | {status} | {assignee} |")
        else:
            lines.append(f"| {i} | {key} | {summary} | {status} | {assignee} |")

    return "\n".join(lines)


def format_with_children_detail(epics: list[dict], children: dict[str, list[dict]]) -> str:
    """Format epics with their unsprinted children listed."""
    lines = []

    for i, epic in enumerate(epics, 1):
        key = epic["key"]
        epic_children = children.get(key, [])
        if not epic_children:
            continue

        lines.append(f"\n**{i}. {key}: {epic['summary']}** ({len(epic_children)} unsprinted)")
        for child in epic_children[:5]:
            lines.append(f"   - {child['key']}: {child['summary'][:50]}... ({child['status']})")
        if len(epic_children) > 5:
            lines.append(f"   ... and {len(epic_children) - 5} more")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Parse Jira epic query results")
    parser.add_argument("input", help="JSON file or - for stdin")
    parser.add_argument("--with-children", "-c", help="Children JSON file")
    parser.add_argument("--detail", "-d", action="store_true", help="Show children detail")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    # Load epics
    if args.input == "-":
        data = json.load(sys.stdin)
    else:
        with open(args.input) as f:
            data = json.load(f)

    epics = parse_epics(data)

    # Load children if provided
    children = None
    if args.with_children:
        with open(args.with_children) as f:
            children = parse_children(json.load(f))

    # Output
    if args.json:
        output = {"epics": epics}
        if children:
            output["children"] = children
        print(json.dumps(output, indent=2))
    elif args.detail and children:
        print(format_with_children_detail(epics, children))
    else:
        print(format_table(epics, children))


if __name__ == "__main__":
    main()
