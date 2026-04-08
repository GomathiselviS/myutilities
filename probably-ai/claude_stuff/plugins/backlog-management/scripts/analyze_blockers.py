#!/usr/bin/env python3
"""Analyze cross-workstream blockers and dependencies from Jira data.

Usage:
    # Analyze blockers from a JSON file of epics with links
    python analyze_blockers.py epics.json

    # Pipe from Jira query results
    cat epics.json | python analyze_blockers.py -

The script expects Jira search results in JSON format with issue links included.
Use fields: key, summary, status, issuelinks, customfield_XXXXX (Workstream)

Example JQL to get data with links:
    project = AAP AND issuetype = Epic AND statusCategory != Done ORDER BY Rank
    Fields: key, summary, status, issuelinks, Workstream, assignee
"""

import argparse
import json
import sys
from collections import defaultdict
from typing import Any


def extract_workstream(fields: dict[str, Any]) -> str:
    """Extract workstream from custom fields."""
    # Common custom field patterns for Workstream
    for key, value in fields.items():
        if "workstream" in key.lower():
            if isinstance(value, dict):
                return value.get("value", "Unknown")
            if isinstance(value, str):
                return value
    return "Unknown"


def parse_issue_links(links: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Parse issue links into categorized relationships."""
    result = {
        "blocks": [],
        "blocked_by": [],
        "relates_to": [],
    }

    for link in links:
        link_type = link.get("type", {}).get("name", "")

        if "outwardIssue" in link:
            target = link["outwardIssue"].get("key", "")
            outward = link.get("type", {}).get("outward", "")
            if "blocks" in outward.lower():
                result["blocks"].append(target)
            else:
                result["relates_to"].append(target)

        if "inwardIssue" in link:
            target = link["inwardIssue"].get("key", "")
            inward = link.get("type", {}).get("inward", "")
            if "blocked" in inward.lower():
                result["blocked_by"].append(target)
            else:
                result["relates_to"].append(target)

    return result


def analyze_blockers(data: dict[str, Any]) -> dict[str, Any]:
    """Analyze blockers and dependencies across epics."""
    issues = data.get("issues", {})
    nodes = issues.get("nodes", [])

    if not nodes:
        # Try alternate format (direct list)
        nodes = data if isinstance(data, list) else []

    # Build issue index
    issue_index = {}
    for issue in nodes:
        key = issue.get("key", "")
        fields = issue.get("fields", {})
        issue_index[key] = {
            "key": key,
            "summary": fields.get("summary", ""),
            "status": fields.get("status", {}).get("name", "Unknown"),
            "workstream": extract_workstream(fields),
            "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
            "links": parse_issue_links(fields.get("issuelinks", [])),
        }

    # Find blockers affecting multiple epics
    blocker_impact = defaultdict(list)
    for key, issue in issue_index.items():
        for blocker in issue["links"]["blocked_by"]:
            blocker_impact[blocker].append(key)

    # Find cross-workstream blockers
    cross_workstream = {}
    for blocker, affected in blocker_impact.items():
        if len(affected) >= 2:
            workstreams = set()
            for key in affected:
                if key in issue_index:
                    workstreams.add(issue_index[key]["workstream"])
            if len(workstreams) >= 2:
                cross_workstream[blocker] = {
                    "affected": affected,
                    "workstreams": list(workstreams),
                }

    # Unassigned epics by workstream
    unassigned_by_workstream = defaultdict(list)
    for key, issue in issue_index.items():
        if not issue["assignee"]:
            unassigned_by_workstream[issue["workstream"]].append(key)

    # High-impact blockers (blocking 2+ issues)
    high_impact_blockers = {k: v for k, v in blocker_impact.items() if len(v) >= 2}

    return {
        "total_issues": len(issue_index),
        "blocker_impact": dict(blocker_impact),
        "cross_workstream_blockers": cross_workstream,
        "high_impact_blockers": high_impact_blockers,
        "unassigned_by_workstream": dict(unassigned_by_workstream),
        "issues": issue_index,
    }


def print_report(analysis: dict[str, Any]) -> None:
    """Print analysis as markdown report."""
    print("## Cross-Workstream Analysis\n")

    # High-impact blockers
    high_impact = analysis.get("high_impact_blockers", {})
    if high_impact:
        print("### High-Impact Blockers")
        print("These issues are blocking multiple epics:\n")
        print("| Blocker | Blocks | Count |")
        print("|---------|--------|-------|")
        for blocker, affected in sorted(high_impact.items(), key=lambda x: -len(x[1])):
            affected_str = ", ".join(affected[:3])
            if len(affected) > 3:
                affected_str += f" (+{len(affected) - 3} more)"
            print(f"| {blocker} | {affected_str} | {len(affected)} |")
        print()

    # Cross-workstream blockers
    cross = analysis.get("cross_workstream_blockers", {})
    if cross:
        print("### Cross-Workstream Blockers")
        print("These blockers affect multiple workstreams:\n")
        print("| Blocker | Workstreams | Affected Epics |")
        print("|---------|-------------|----------------|")
        for blocker, info in cross.items():
            ws = ", ".join(info["workstreams"])
            affected = ", ".join(info["affected"][:3])
            print(f"| {blocker} | {ws} | {affected} |")
        print()

    # Unassigned epics
    unassigned = analysis.get("unassigned_by_workstream", {})
    if unassigned:
        print("### Unassigned Epics by Workstream")
        print("| Workstream | Unassigned | Epics |")
        print("|------------|------------|-------|")
        for ws, epics in sorted(unassigned.items()):
            epics_str = ", ".join(epics[:3])
            if len(epics) > 3:
                epics_str += f" (+{len(epics) - 3} more)"
            print(f"| {ws} | {len(epics)} | {epics_str} |")
        print()

    # Summary
    total = analysis.get("total_issues", 0)
    blocker_count = len(analysis.get("blocker_impact", {}))
    print("### Summary")
    print(f"- Total epics analyzed: {total}")
    print(f"- Issues acting as blockers: {blocker_count}")
    print(f"- High-impact blockers (2+ affected): {len(high_impact)}")
    print(f"- Cross-workstream blockers: {len(cross)}")


def main():
    parser = argparse.ArgumentParser(description="Analyze cross-workstream blockers")
    parser.add_argument("input", help="JSON file path or '-' for stdin")
    parser.add_argument("--json", "-j", action="store_true", help="Output raw JSON instead of markdown")
    args = parser.parse_args()

    # Read input
    if args.input == "-":
        data = json.load(sys.stdin)
    else:
        with open(args.input) as f:
            data = json.load(f)

    analysis = analyze_blockers(data)

    if args.json:
        print(json.dumps(analysis, indent=2))
    else:
        print_report(analysis)


if __name__ == "__main__":
    main()
