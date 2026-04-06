# backlog-management

Jira backlog prioritization and epic management tools — list backlog epics and reorder their child tickets.

## Installation

### Claude Code

```shell
/plugin marketplace add ansible/ansible-mgr-ai
/plugin install backlog-management@ansible-mgr-ai
```

### Other tools

All files are plain Markdown. See [RUNTIMES.md](../../RUNTIMES.md) for details.

## Quick start

```
# List backlog epics with unsprinted children
/backlog-management:list-aca-epics

# Reorder backlog with specific epic priorities
/backlog-management:list-aca-epics --reorder ACA-5367 ACA-5382 ACA-4964
```

## Commands

| Command | Description | Review |
| :------ | :---------- | :----- |
| `/backlog-management:list-aca-epics` | List backlog epics and reorder their child tickets to the top of the backlog | No |

## Skills

| Skill | Loaded By | Purpose |
| :---- | :-------- | :------ |
| `list-aca-epics` | `list-aca-epics` | Instructions for listing and reordering backlog epics |

## Configuration

Edit `config.yaml` with your team's settings:
- `jira.base_url` - Your Jira instance URL
- `jira.email` - Your Jira email
- `epic_jql` - JQL query to filter epics
- `backlog_jql` - JQL query for backlog ranking anchor

## Prerequisites

- **Environment variables:**
  ```bash
  export JIRA_EMAIL="your-email@example.com"
  export JIRA_API_TOKEN="your-api-token"
  ```
  Get your API token from: https://id.atlassian.com/manage-profile/security/api-tokens

- **Python dependencies:**
  ```bash
  pip install requests pyyaml
  ```

## How it works

1. Fetches epics matching the `epic_jql` query from `config.yaml`
2. Filters to only show epics with unsprinted child tickets
3. When reordering, moves the child tickets of selected epics to the top of the backlog

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for how to add commands to this plugin.
