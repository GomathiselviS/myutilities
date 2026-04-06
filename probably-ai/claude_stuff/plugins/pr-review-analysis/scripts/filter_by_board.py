#!/usr/bin/env python3
"""
Filter Jira Issues by Board ID

Filters Jira API response to only include issues that belong to sprints
on a specific board. This is necessary because Jira's JQL doesn't directly
support filtering by board ID in all cases.

Usage:
    python filter_by_board.py --input jira_data.json --board 10910 --output filtered.json

    Or via stdin/stdout:
    cat jira_data.json | python filter_by_board.py --board 10910 > filtered.json

The script expects Jira data with the customfield_10020 (Sprint) field,
which contains sprint objects with boardId attributes.
"""

import argparse
import json
import re
import sys
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter Jira issues by board ID")
    parser.add_argument("--input", "-i", type=str, help="Input Jira JSON file (default: stdin)")
    parser.add_argument("--output", "-o", type=str, help="Output JSON file (default: stdout)")
    parser.add_argument(
        "--board",
        "-b",
        type=int,
        required=True,
        help="Jira board ID to filter by (required)",
    )
    parser.add_argument(
        "--status",
        "-s",
        type=str,
        default="Review",
        help="Status to filter by (default: Review)",
    )
    parser.add_argument(
        "--extract-prs",
        action="store_true",
        help="Also extract and output PR URLs from filtered issues",
    )
    return parser.parse_args()


def load_jira_data(input_file: str | None) -> dict:
    """Load Jira data from file or stdin."""
    if input_file:
        with open(input_file) as f:
            return json.load(f)
    return json.load(sys.stdin)


def filter_by_board(jira_data: dict, board_id: int, status_filter: str | None = None) -> dict:
    """
    Filter Jira issues to only those in active sprints on the specified board.

    Args:
        jira_data: Raw Jira API response with issues
        board_id: The Jira board ID to filter by
        status_filter: Optional status name to filter by (case-insensitive)

    Returns:
        Filtered Jira data with the same structure
    """
    issues = jira_data.get("issues", {}).get("nodes", [])
    if not issues:
        issues = jira_data.get("issues", [])

    filtered_issues = []
    for issue in issues:
        fields = issue.get("fields", {})

        # Check status if filter provided
        if status_filter:
            status = fields.get("status", {}).get("name", "")
            if status.lower() != status_filter.lower():
                continue

        # Check sprint belongs to target board
        sprints = fields.get("customfield_10020", []) or []
        for sprint in sprints:
            if isinstance(sprint, dict):
                if sprint.get("boardId") == board_id and sprint.get("state") == "active":
                    filtered_issues.append(issue)
                    break

    # Reconstruct the response structure
    result = dict(jira_data)
    if "issues" in result and isinstance(result["issues"], dict):
        result["issues"] = dict(result["issues"])
        result["issues"]["nodes"] = filtered_issues
        result["issues"]["totalCount"] = len(filtered_issues)
    else:
        result["issues"] = filtered_issues

    return result


def extract_pr_urls_from_adf(adf_content: dict | str | None) -> set[str]:
    """Extract PR URLs from Atlassian Document Format content."""
    pr_pattern = re.compile(r"https://github\.com/[^/]+/[^/]+/pull/\d+")
    prs: set[str] = set()

    if not adf_content:
        return prs

    if isinstance(adf_content, str):
        prs.update(pr_pattern.findall(adf_content))
        return prs

    # Handle ADF structure (dict with content array)
    def walk_adf(node: dict | list) -> None:
        if isinstance(node, dict):
            # Check for text content
            if node.get("type") == "text":
                text = node.get("text", "")
                prs.update(pr_pattern.findall(text))
            # Check for link marks
            for mark in node.get("marks", []):
                if mark.get("type") == "link":
                    href = mark.get("attrs", {}).get("href", "")
                    prs.update(pr_pattern.findall(href))
            # Recurse into content
            for child in node.get("content", []):
                walk_adf(child)
        elif isinstance(node, list):
            for item in node:
                walk_adf(item)

    walk_adf(adf_content)
    return prs


def extract_pr_urls(jira_data: dict) -> dict[str, list[str]]:
    """Extract PR URLs from filtered Jira issues."""
    pr_pattern = re.compile(r"https://github\.com/[^/]+/[^/]+/pull/\d+")

    issues = jira_data.get("issues", {}).get("nodes", [])
    if not issues:
        issues = jira_data.get("issues", [])

    issue_prs: dict[str, list[str]] = {}
    all_prs: set[str] = set()

    for issue in issues:
        key = issue.get("key", "")
        prs: set[str] = set()
        fields = issue.get("fields", {})

        # Extract from Git Pull Request field (customfield_10875) - primary source
        git_pr_field = fields.get("customfield_10875")
        prs.update(extract_pr_urls_from_adf(git_pr_field))

        # Extract from comments
        comment_data = fields.get("comment", {})
        comments = comment_data.get("comments", []) if isinstance(comment_data, dict) else []
        for comment in comments:
            body = str(comment.get("body", ""))
            prs.update(pr_pattern.findall(body))

        # Extract from description
        description = str(fields.get("description", "") or "")
        prs.update(pr_pattern.findall(description))

        if prs:
            issue_prs[key] = sorted(prs)
            all_prs.update(prs)

    return {
        "by_ticket": issue_prs,
        "unique_prs": sorted(all_prs),
        "total_tickets": len(issues),
        "tickets_with_prs": len(issue_prs),
    }


def main() -> None:
    args = parse_args()

    jira_data = load_jira_data(args.input)
    filtered_data = filter_by_board(jira_data, args.board, args.status)

    output: dict[str, Any] = {"filtered_jira": filtered_data}

    if args.extract_prs:
        pr_data = extract_pr_urls(filtered_data)
        output["pr_extraction"] = pr_data

    # Output
    output_json = json.dumps(
        output if args.extract_prs else filtered_data,
        indent=2,
    )

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_json)
        # Print summary to stderr
        issues = filtered_data.get("issues", {}).get("nodes", [])
        if not issues:
            issues = filtered_data.get("issues", [])
        print(f"Filtered to {len(issues)} issues on board {args.board}", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
