#!/usr/bin/env python3
"""
Backlog Epic Prioritization Tool

Fetches epics from Jira, allows user to specify priorities,
and reorders them using the Agile API.

Requirements:
    pip install requests pyyaml

Environment variables:
    JIRA_API_TOKEN: Your Jira API token (https://id.atlassian.com/manage-profile/security/api-tokens)
    JIRA_EMAIL: Override email from config (optional)
    JIRA_BASE_URL: Override base URL from config (optional)

Configuration:
    Edit config.yaml in the plugin directory to customize JQL queries and settings.
"""

import argparse
import os
import sys
from pathlib import Path

import requests
import yaml
from requests.auth import HTTPBasicAuth

# Load configuration
CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_config():
    """Load configuration from config.yaml."""
    if not CONFIG_PATH.exists():
        print(f"Error: Config file not found at {CONFIG_PATH}")
        print("Copy config.yaml.example to config.yaml and customize it.")
        sys.exit(1)

    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


CONFIG = load_config()

# Configuration with environment variable overrides
JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", CONFIG.get("jira", {}).get("base_url", ""))
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", CONFIG.get("jira", {}).get("email", ""))
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN")

# JQL queries from config (normalize multiline strings)
EPIC_JQL = " ".join(CONFIG.get("epic_jql", "").split())
BACKLOG_JQL = " ".join(CONFIG.get("backlog_jql", "").split())


def get_auth():
    """Get authentication for Jira API."""
    if not JIRA_EMAIL or not JIRA_API_TOKEN:
        print("Error: JIRA_EMAIL and JIRA_API_TOKEN environment variables required.")
        print("Get your API token at: https://id.atlassian.com/manage-profile/security/api-tokens")
        sys.exit(1)
    return HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)


def get_unsprinted_children(epic_key):
    """Get all child issues of an epic that are not in any sprint."""
    url = f"{JIRA_BASE_URL}/rest/api/3/search/jql"
    jql = f'"Parent" = {epic_key} AND Sprint is EMPTY ORDER BY Rank'
    params = {
        "jql": jql,
        "fields": "key,summary",
        "maxResults": 100
    }

    response = requests.get(url, params=params, auth=get_auth())
    if not response.ok:
        return []

    data = response.json()
    return [issue["key"] for issue in data.get("issues", [])]


def has_unsprinted_children(epic_key):
    """Check if an epic has at least one child issue not in any sprint."""
    return len(get_unsprinted_children(epic_key)) > 0


def fetch_backlog_epics():
    """Fetch backlog epics using JQL search."""
    if not EPIC_JQL:
        print("Error: epic_jql not configured in config.yaml.")
        sys.exit(1)

    url = f"{JIRA_BASE_URL}/rest/api/3/search/jql"
    params = {
        "jql": EPIC_JQL,
        "fields": "summary,status,assignee",
        "maxResults": 50
    }

    response = requests.get(url, params=params, auth=get_auth())
    if not response.ok:
        print(f"Error {response.status_code}: {response.text}")
        response.raise_for_status()

    data = response.json()
    epics = []

    print("Fetching epics from backlog...")
    for issue in data.get("issues", []):
        epic_key = issue["key"]
        fields = issue["fields"]

        # Only include epics that have at least one child not in a sprint
        if has_unsprinted_children(epic_key):
            assignee = fields.get("assignee")
            epics.append({
                "key": epic_key,
                "summary": fields["summary"],
                "status": fields["status"]["name"],
                "assignee": assignee["displayName"] if assignee else "Unassigned"
            })

    return epics


def display_epics(epics, title="Backlog Epics"):
    """Display epics in a table format."""
    print(f"\n## {title}\n")
    print(f"| {'#':<3} | {'Key':<12} | {'Summary':<60} | {'Status':<10} | {'Assignee':<20} |")
    print(f"|{'-'*5}|{'-'*14}|{'-'*62}|{'-'*12}|{'-'*22}|")

    for i, epic in enumerate(epics, 1):
        summary = epic["summary"][:57] + "..." if len(epic["summary"]) > 60 else epic["summary"]
        print(f"| {i:<3} | {epic['key']:<12} | {summary:<60} | {epic['status']:<10} | {epic['assignee']:<20} |")


def get_user_priorities(epics):
    """Get priority epic keys from user."""
    epic_keys = {e["key"] for e in epics}

    print("\n## Enter Priority Epics")
    print("Enter epic keys in priority order (highest first), one per line.")
    print("Type 'done' when finished.\n")

    priorities = []
    i = 1
    while True:
        key = input(f"Priority {i}: ").strip().upper()
        if key == "DONE" or key == "":
            return priorities
        if key not in epic_keys:
            print(f"  Invalid key '{key}'. Please enter a valid epic key from the list.")
            continue
        if key in priorities:
            print(f"  '{key}' already added. Please enter a different epic.")
            continue
        priorities.append(key)
        i += 1

    return priorities


def get_first_backlog_ticket():
    """Get the first ticket in the backlog to use as anchor."""
    url = f"{JIRA_BASE_URL}/rest/api/3/search/jql"
    params = {
        "jql": BACKLOG_JQL,
        "fields": "key",
        "maxResults": 1
    }
    response = requests.get(url, params=params, auth=get_auth())
    if response.ok:
        data = response.json()
        issues = data.get("issues", [])
        if issues:
            return issues[0]["key"]
    return None


def move_issue_before(issue_key, rank_before):
    """Move an issue to rank before another issue."""
    url = f"{JIRA_BASE_URL}/rest/agile/1.0/issue/rank"
    payload = {
        "issues": [issue_key],
        "rankBeforeIssue": rank_before
    }
    response = requests.put(url, json=payload, auth=get_auth())
    response.raise_for_status()
    return True


def reorder_backlog(priorities, epics):
    """
    Reorder backlog by moving priority epics and their unsprinted children to the top.
    Uses Jira Agile API to rank issues.
    """
    if not priorities:
        print("No priorities specified. Skipping reorder.")
        return

    print("\n## Reordering Backlog in Jira...")

    # Collect all tickets to move: for each epic, get its unsprinted children
    all_tickets_to_move = []
    for epic_key in priorities:
        children = get_unsprinted_children(epic_key)
        print(f"  {epic_key}: found {len(children)} unsprinted tickets")
        all_tickets_to_move.extend(children)

    if not all_tickets_to_move:
        print("No unsprinted tickets found to reorder.")
        return

    print(f"\nMoving {len(all_tickets_to_move)} tickets to top of backlog...")

    # Move tickets in reverse order, each one ranking before the previous
    moved_count = 0
    # Start by finding the current top of backlog as initial anchor
    anchor = get_first_backlog_ticket()
    if not anchor:
        print("Could not find anchor ticket in backlog.")
        return

    for ticket_key in reversed(all_tickets_to_move):
        try:
            move_issue_before(ticket_key, anchor)
            anchor = ticket_key  # Next ticket will rank before this one
            moved_count += 1
        except requests.exceptions.HTTPError as e:
            print(f"  Failed to move {ticket_key}: {e}")

    print(f"\nMoved {moved_count} tickets to top of backlog!")


def display_final_order(priorities, epics):
    """Display the prioritized epics and their moved tickets."""
    print("\n" + "="*100)
    print("\n## Tickets Moved to Top of Backlog\n")

    epic_dict = {e["key"]: e for e in epics}
    for epic_key in priorities:
        epic = epic_dict.get(epic_key, {"summary": "Unknown"})
        children = get_unsprinted_children(epic_key)
        summary = epic["summary"][:60] + "..." if len(epic["summary"]) > 63 else epic["summary"]
        print(f"### {epic_key}: {summary}")
        if children:
            for ticket in children:
                print(f"  - {ticket}")
        else:
            print("  (no unsprinted tickets)")
        print()


def main():
    parser = argparse.ArgumentParser(description="ACA Backlog Epic Prioritization Tool")
    parser.add_argument("--list", action="store_true", help="List backlog epics and exit")
    parser.add_argument("--reorder", nargs="+", metavar="KEY", help="Reorder backlog with given epic keys as priorities")
    args = parser.parse_args()

    # Fetch epics
    epics = fetch_backlog_epics()

    if not epics:
        print("No backlog epics found.")
        return

    # List-only mode
    if args.list:
        print(f"Found {len(epics)} epics in backlog.\n")
        display_epics(epics, "Current Backlog (New/Backlog status)")
        return

    # Reorder mode with provided keys
    if args.reorder:
        epic_keys = {e["key"] for e in epics}
        priorities = [k.upper() for k in args.reorder]

        # Validate keys
        invalid = [k for k in priorities if k not in epic_keys]
        if invalid:
            print(f"Error: Invalid epic keys: {', '.join(invalid)}")
            print(f"Valid keys: {', '.join(sorted(epic_keys))}")
            sys.exit(1)

        print(f"Reordering backlog with priorities: {', '.join(priorities)}")
        reorder_backlog(priorities, epics)
        display_final_order(priorities, epics)
        return

    # Interactive mode (default)
    print("# ACA Backlog Epic Prioritization Tool")
    print("="*50)
    print(f"\nFound {len(epics)} epics in backlog.")
    display_epics(epics, "Current Backlog (New/Backlog status)")

    priorities = get_user_priorities(epics)

    if not priorities:
        print("No priorities specified. Exiting.")
        return

    print(f"\nYou selected: {', '.join(priorities)}")
    confirm = input("Reorder backlog in Jira? (yes/no): ").strip().lower()

    if confirm == "yes":
        reorder_backlog(priorities, epics)
    else:
        print("Skipping Jira reorder.")

    display_final_order(priorities, epics)


if __name__ == "__main__":
    main()
