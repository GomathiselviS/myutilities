#!/usr/bin/env python3
"""Reorder Jira backlog by moving tickets before an anchor.

Usage:
    python reorder_backlog.py --tickets ACA-5383 ACA-5378 ACA-5379 --anchor ACA-5327

Environment variables:
    JIRA_BASE_URL: Jira instance URL (default: https://redhat.atlassian.net)
    JIRA_USER: Email address for Atlassian Cloud authentication
    JIRA_TOKEN: API token for authentication

The script moves tickets to rank before the anchor in the order specified.
It processes tickets in reverse order so the final ranking matches the input order.
"""

import argparse
import base64
import os
import sys

import requests


def get_auth_headers() -> dict[str, str]:
    """Get authentication headers for Jira API."""
    token = os.environ.get("JIRA_TOKEN")
    user = os.environ.get("JIRA_USER")

    if not token:
        print("Error: JIRA_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    # Use Basic auth if JIRA_USER is provided (Atlassian Cloud)
    if user:
        credentials = base64.b64encode(f"{user}:{token}".encode()).decode()
        return {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }

    # Fall back to Bearer token (Jira Server/Data Center)
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def rank_issue(base_url: str, issue_key: str, rank_before: str, headers: dict) -> bool:
    """Move an issue to rank before another issue.

    Args:
        base_url: Jira instance URL
        issue_key: Key of the issue to move
        rank_before: Key of the issue to rank before
        headers: Authentication headers

    Returns:
        True if successful, False otherwise
    """
    url = f"{base_url}/rest/agile/1.0/issue/rank"
    payload = {
        "issues": [issue_key],
        "rankBeforeIssue": rank_before,
    }

    try:
        response = requests.put(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        print(f"  Moved {issue_key} before {rank_before}")
        return True
    except requests.exceptions.HTTPError as e:
        print(f"  Failed to move {issue_key}: {e}", file=sys.stderr)
        return False
    except requests.exceptions.RequestException as e:
        print(f"  Error moving {issue_key}: {e}", file=sys.stderr)
        return False


def reorder_backlog(tickets: list[str], anchor: str, base_url: str) -> tuple[int, int]:
    """Reorder tickets to the top of the backlog.

    Args:
        tickets: List of ticket keys in priority order (highest first)
        anchor: Current top of backlog to rank before
        base_url: Jira instance URL

    Returns:
        Tuple of (success_count, total_count)
    """
    headers = get_auth_headers()
    success_count = 0
    current_anchor = anchor

    # Process in reverse order so final ranking matches input order
    for ticket in reversed(tickets):
        if rank_issue(base_url, ticket, current_anchor, headers):
            success_count += 1
            current_anchor = ticket

    return success_count, len(tickets)


def main():
    parser = argparse.ArgumentParser(description="Reorder Jira backlog tickets")
    parser.add_argument(
        "--tickets",
        "-t",
        nargs="+",
        required=True,
        help="Ticket keys in priority order (highest first)",
    )
    parser.add_argument(
        "--anchor",
        "-a",
        required=True,
        help="Current top of backlog (tickets will be moved before this)",
    )
    parser.add_argument(
        "--base-url",
        "-u",
        default=os.environ.get("JIRA_BASE_URL", "https://redhat.atlassian.net"),
        help="Jira base URL (default: $JIRA_BASE_URL or https://redhat.atlassian.net)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be done without making changes",
    )
    args = parser.parse_args()

    print(f"Reordering {len(args.tickets)} tickets before {args.anchor}")
    print(f"Target order: {', '.join(args.tickets)}")
    print()

    if args.dry_run:
        print("Dry run - no changes will be made")
        print()
        current_anchor = args.anchor
        for ticket in reversed(args.tickets):
            print(f"  Would move {ticket} before {current_anchor}")
            current_anchor = ticket
        print()
        print(f"Final order: {', '.join(args.tickets)}, {args.anchor}, ...")
        return

    success, total = reorder_backlog(args.tickets, args.anchor, args.base_url)
    print()
    print(f"Moved {success} of {total} tickets successfully")

    if success < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
