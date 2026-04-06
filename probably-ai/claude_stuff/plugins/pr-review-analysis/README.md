# pr-review-analysis

Pull request review analytics for Jira sprint tickets.

## Overview

This plugin analyzes the health of pull requests associated with Jira tickets
in review during the active sprint. It extracts PR links from the Jira "Git Pull
Request" field (`customfield_10875`), comments, and descriptions, then evaluates
each PR for:

- **Review duration** — How long PRs have been waiting for review
- **Comment resolution** — Whether review feedback has been addressed
- **Resolution time** — How quickly authors respond to feedback
- **Reviewer engagement** — Approval counts, pending reviewers, and response rates

## Commands

### analyze-sprint-prs

```
/pr-review-analysis:analyze-sprint-prs [jira-project-key] --board BOARD_ID
```

Generates a comprehensive PR review health report for the active sprint on a
specific Jira board, including:

- Sprint summary with PR counts by status
- Review velocity metrics (avg duration, time to first review)
- Flagged PRs needing attention with specific recommendations
- Full table of all PRs in review

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `jira-project-key` | No | Jira project key (e.g., ACA). Prompts if omitted. |
| `--board BOARD_ID` | **Yes** | Jira board ID to filter tickets. |

## Scripts

### filter_by_board.py

Filters Jira API response to only include tickets in sprints on a specific board.

```bash
python scripts/filter_by_board.py --input jira.json --board 10910 --output filtered.json

# Also extract PR URLs
python scripts/filter_by_board.py --input jira.json --board 10910 --extract-prs
```

### generate_report.py

Generates a markdown PR review health report from Jira and GitHub data.

```bash
python scripts/generate_report.py \
  --jira jira.json \
  --prs prs.json \
  --project ACA \
  --board 10910
```

### fetch_github_prs.py

Fetches PR details from GitHub for a list of PR URLs.

```bash
python scripts/fetch_github_prs.py --input pr_urls.txt --output prs.json

# Or pipe URLs
echo "https://github.com/org/repo/pull/123" | python scripts/fetch_github_prs.py
```

## PR Extraction Sources

PRs are extracted from Jira tickets in the following order:

1. **Git Pull Request field** (`customfield_10875`) — Primary source, populated by GitHub-Jira integration
2. **Comments** — Scanned for GitHub/GitLab/Bitbucket PR URLs
3. **Description** — Checked for PR URL patterns

## Use Cases

- **Sprint health checks** — Identify PRs blocking sprint completion
- **Review load balancing** — Spot overloaded or unresponsive reviewers
- **Process improvement** — Track review velocity trends over time
- **Standup preparation** — Surface PRs needing discussion

## Prerequisites

### Jira (Atlassian MCP)

The Atlassian MCP plugin must be configured with valid credentials:

| Variable | Description |
|----------|-------------|
| `ATLASSIAN_API_TOKEN` | API token from https://id.atlassian.com/manage-profile/security/api-tokens |
| `ATLASSIAN_EMAIL` | Email associated with the Atlassian account |
| `ATLASSIAN_SITE_URL` | Your Jira instance URL (e.g., `https://yourcompany.atlassian.net`) |

Required Jira permissions: Browse projects, View development tools

### GitHub

One of the following authentication methods:

| Method | Setup |
|--------|-------|
| `gh` CLI | Run `gh auth login` once |
| `GITHUB_TOKEN` | Set env var with a personal access token (`repo` scope for private repos) |

## Example Output

```markdown
## Sprint PR Review Analysis

**Project:** ACA
**Board:** 10910
**Analysis Date:** 2026-04-03

### Summary

| Metric | Value |
|--------|-------|
| Tickets in Review | 13 |
| PRs Found | 8 |
| Approved & Ready | 1 |
| Changes Requested | 1 |
| Stale (>2 days) | 2 |

### PRs Needing Attention

#### hashicorp.vault#70 — New module to rotate credentials
- Jira: ACA-5350
- Status: IN_REVIEW
- Open for: 3 days
- Flags: ACTIVE
- Recommendation: Review in progress, monitor for completion
```
