---
name: backlog-management:list-aca-epics
description: List and prioritize epics from a Jira backlog board
user_invocable: true
---

# List Backlog Epics

List and prioritize epics from a Jira backlog. Configure the board and filters in `config.yaml`.

## Instructions

Follow these steps to list and reorder backlog epics:

### Step 1: List current backlog

Run from the plugin's base directory (`plugins/backlog-management/`):
```bash
python3 scripts/reorder_backlog.py --list
```

This displays all backlog epics matching the `epic_jql` query in `config.yaml`.

**IMPORTANT:** Copy the full table output into your response so the user can see it.

### Step 2: Ask user for priorities

Ask which epics they want at the top of the backlog. Get the epic keys in priority order.

### Step 3: Reorder the backlog

Run with the user's priority keys:
```bash
python3 scripts/reorder_backlog.py --reorder KEY1 KEY2 KEY3 ...
```

Example:
```bash
python3 scripts/reorder_backlog.py --reorder PROJ-123 PROJ-456 PROJ-789
```

### Filtering Logic

1. Fetches epics matching the `epic_jql` query from `config.yaml`.

2. Filters to only include epics that have at least one child ticket not in any sprint.

3. When reordering, moves the **child tickets** (not the epics) of selected epics to the top of the backlog.

## Configuration

Edit `config.yaml` to customize:
- `jira.base_url` - Jira instance URL
- `jira.email` - Your Jira email
- `epic_jql` - JQL query for fetching epics
- `backlog_jql` - JQL query for backlog ranking anchor

## Environment Variables

Required:
- `JIRA_EMAIL` - Your Jira email
- `JIRA_API_TOKEN` - Your Jira API token (https://id.atlassian.com/manage-profile/security/api-tokens)
