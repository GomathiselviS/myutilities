# backlog-management

Jira backlog management tools — scripts for reordering backlog tickets and generating reports.

## Installation

### Claude Code

```shell
/plugin marketplace add ansible/ansible-mgr-ai
/plugin install backlog-management@ansible-mgr-ai
```

### Other tools

All files are plain Markdown. See [RUNTIMES.md](../../RUNTIMES.md) for details.

## Skills

| Skill | Purpose |
| :---- | :------ |
| `backlog-prioritization` | Patterns for querying and reordering Jira backlogs |

## Scripts

| Script | Purpose |
| :----- | :------ |
| `scripts/generate_backlog_report.py` | Generate markdown tables from Jira query JSON |
| `scripts/reorder_backlog.py` | Reorder backlog tickets using Jira Agile API |
| `scripts/prioritization_history.py` | Track prioritization decisions and detect patterns |
| `scripts/analyze_blockers.py` | Analyze cross-workstream blockers and dependencies |

### Generate Report

```bash
# From file
python plugins/backlog-management/scripts/generate_backlog_report.py results.json --project AAP

# From stdin
cat results.json | python plugins/backlog-management/scripts/generate_backlog_report.py - -p ACA
```

The report automatically:
- Flags In Progress epics with unsprinted children (⚠️) — recommend prioritizing these first
- Calls out unassigned epics (📋) — consider assigning an owner

### Reorder Backlog

The Atlassian MCP tools don't support the Jira Agile ranking API. Use this script to reorder tickets:

```bash
# For Atlassian Cloud (requires both user email and API token)
export JIRA_USER="your-email@company.com"
export JIRA_TOKEN="your-api-token"

python plugins/backlog-management/scripts/reorder_backlog.py \
  --tickets ACA-5383 ACA-5378 ACA-5379 \
  --anchor ACA-5327

# Preview changes without modifying Jira
python plugins/backlog-management/scripts/reorder_backlog.py \
  --tickets ACA-5383 ACA-5378 \
  --anchor ACA-5327 \
  --dry-run
```

#### Environment Variables

| Variable | Required | Description |
| :------- | :------- | :---------- |
| `JIRA_USER` | Yes (Cloud) | Email address for Atlassian Cloud authentication |
| `JIRA_TOKEN` | Yes | API token (Cloud) or Personal Access Token (Server/Data Center) |
| `JIRA_BASE_URL` | No | Jira instance URL (default: `https://redhat.atlassian.net`) |

For Jira Server/Data Center, only `JIRA_TOKEN` is required (uses Bearer auth).

### Track Prioritization History

Log decisions to build a history for pattern detection:

```bash
# Log a prioritization decision
python plugins/backlog-management/scripts/prioritization_history.py log \
  --epic AAP-12345 \
  --reason technical-dependency \
  --note "Vault KV v2 blocking amazon.aws credential lookup"

# View recent history
python plugins/backlog-management/scripts/prioritization_history.py show

# Detect patterns (requires 5+ logged decisions)
python plugins/backlog-management/scripts/prioritization_history.py patterns

# Find epics that keep getting reprioritized
python plugins/backlog-management/scripts/prioritization_history.py stale
```

### Analyze Cross-Workstream Blockers

Identify high-impact blockers across teams:

```bash
# Analyze from Jira export
python plugins/backlog-management/scripts/analyze_blockers.py epics.json

# Output as JSON
python plugins/backlog-management/scripts/analyze_blockers.py epics.json --json
```

## Prerequisites

- **Atlassian MCP server**: Must be configured and authenticated in Claude Code. Navigate to `/plugins` and authenticate with the Atlassian plugin. Used for querying epics and tickets.
- **Jira access**: Your authenticated account needs access to the target project's board.
- **Jira API credentials** (for backlog reordering):
  - `JIRA_USER`: Your Atlassian account email
  - `JIRA_TOKEN`: Atlassian API token — generate at https://id.atlassian.com/manage-profile/security/api-tokens
  - **Security:** Never output `JIRA_TOKEN` values to stdout, logs, or confirmation messages

The Atlassian MCP tools don't support the Jira Agile ranking API, so the `reorder_backlog.py` script requires separate API credentials.

## How it works

1. Queries epics in the given project using Atlassian MCP tools
2. Filters to only show epics with unsprinted child tickets
3. Helps you decide which epics to prioritize (can suggest based on dependencies, blockers, etc.)
4. When prioritizing, moves the child tickets of selected epics to the top of the backlog

## Integration

This plugin uses the `jira-context` skill from the `integrations` plugin for Jira connectivity. No manual credential management required — authentication is handled by the Atlassian MCP server.

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for how to add commands to this plugin.
