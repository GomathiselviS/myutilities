# probably-ai

AI-related tools and Claude Code plugins.

## Contents

### claude_stuff/

Claude Code plugins for engineering management workflows:

| Plugin | Description |
|--------|-------------|
| **backlog-management** | Jira backlog prioritization and epic management. List epics with unsprinted children and reorder tickets. |
| **pr-review-analysis** | PR review analytics for Jira sprint tickets. Tracks review duration, comment resolution, and reviewer engagement. |

## Installation

```shell
/plugin marketplace add ansible/ansible-mgr-ai
/plugin install backlog-management@ansible-mgr-ai
/plugin install pr-review-analysis@ansible-mgr-ai
```

## Prerequisites

- Jira API token (`JIRA_API_TOKEN` or `ATLASSIAN_API_TOKEN`)
- GitHub CLI (`gh auth login`) or `GITHUB_TOKEN` for PR analysis
