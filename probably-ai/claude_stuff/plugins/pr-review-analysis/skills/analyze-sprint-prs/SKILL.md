---
name: analyze-sprint-prs
description: "Analyze PR review health for Jira tickets in review during the active sprint. When an agent needs to: (1) Check PR review status for sprint tickets, (2) Find stale or blocked PRs, (3) Measure review velocity metrics, (4) Identify PRs needing attention, or (5) Generate a sprint PR health report. Extracts PRs from Jira comments and fields, fetches GitHub PR details, and generates actionable recommendations."
---

# Analyze Sprint PRs

## Keywords
pr review, pull request status, sprint prs, review health, stale prs, blocked prs, code review, pr analysis, review velocity, jira sprint, github pr, pr metrics, review duration, unreviewed prs

## Overview

Analyze the health of pull requests associated with Jira tickets in review during the active sprint. This skill extracts PR links from Jira, fetches PR details from GitHub, calculates review metrics, and generates a report with actionable recommendations.

**Use this skill when:** Users want to check PR review status for their sprint, find blocked or stale PRs, or generate a sprint PR health report.

---

## Prerequisites

**Jira (Atlassian MCP):**
- `ATLASSIAN_API_TOKEN` — API token from https://id.atlassian.com/manage-profile/security/api-tokens
- `ATLASSIAN_EMAIL` — Email associated with the Atlassian account
- `ATLASSIAN_SITE_URL` — Your Jira instance URL (e.g., `https://yourcompany.atlassian.net`)

**GitHub:**
- `gh` CLI authenticated — Run `gh auth login` once
- Or `GITHUB_TOKEN` environment variable with `repo` scope

---

## Workflow

Follow this 5-step process to analyze sprint PRs:

### Step 1: Get Jira Project, Site, and Board

Ask the user for:
- **Jira site URL** (e.g., `https://redhat.atlassian.net`)
- **Jira project key** (e.g., `ACA`, `AAP`, `AWX`)
- **Board ID** (required, e.g., `10910`)

### Step 2: Query Jira for Tickets in Review

Use `searchJiraIssuesUsingJql` to find tickets:

```jql
project = {project_key} AND sprint in openSprints() AND status = "Review"
```

Request these fields: `summary`, `status`, `assignee`, `comment`, `created`, `updated`, `customfield_10020`, `customfield_10875`

**Note:** `customfield_10875` is the "Git Pull Request" field in Jira Details.

**Important:** The `customfield_10020` field contains sprint data including `boardId`. Filter results to only include tickets where the sprint's `boardId` matches the specified board.

Use the board filtering script:
```bash
python plugins/pr-review-analysis/scripts/filter_by_board.py \
  --input jira_data.json \
  --board {board_id} \
  --output filtered_jira.json
```

If no results, try a broader query without status filter and filter manually for statuses containing "review".

### Step 3: Extract PR URLs from Jira

For each ticket, scan for PR URLs in:

1. **Git Pull Request field** (`customfield_10875`) — Primary source, populated by GitHub-Jira integration

2. **Comments** — Look for patterns:
   - `https://github.com/{owner}/{repo}/pull/{number}`
   - `https://gitlab.com/{group}/{project}/-/merge_requests/{number}`
   - `https://bitbucket.org/{workspace}/{repo}/pull-requests/{number}`

3. **Description** — Check issue description for PR links

4. **Remote links** — Use `getJiraIssueRemoteIssueLinks` if available

Deduplicate PR URLs across all tickets.

### Step 4: Fetch PR Details from GitHub

For each GitHub PR URL, use the fetch script or `gh` CLI directly:

```bash
# Using the fetch script (recommended)
python plugins/pr-review-analysis/scripts/fetch_github_prs.py \
  --input pr_urls.txt \
  --output prs.json

# Or directly with gh CLI
gh pr view {number} -R {owner}/{repo} --json number,title,state,createdAt,updatedAt,author,reviewDecision,reviews,isDraft,url
```

Collect results into a JSON array.

### Step 5: Generate Report

Use the report generation script:

```bash
python plugins/pr-review-analysis/scripts/generate_report.py \
  --jira jira_data.json \
  --prs pr_data.json \
  --project {project_key}
```

Or calculate metrics manually and format the report.

---

## PR Health Metrics

### Flags

| Flag | Condition | Action |
|------|-----------|--------|
| STALE | No activity > 2 days | Follow up with author/reviewers |
| BLOCKED | Changes requested, no new commits | Author needs to address feedback |
| UNREVIEWED | Open > 2 days, no reviews | Assign reviewers |
| DRAFT | PR is in draft state | Wait for author to mark ready |
| READY | Approved, ready to merge | Merge or address final items |

### Review Decision States

| State | Meaning |
|-------|---------|
| APPROVED | Has required approvals |
| CHANGES_REQUESTED | Reviewer requested changes |
| REVIEW_REQUIRED | Needs reviewer approval |
| PENDING | Reviews in progress |

---

## Output Format

Generate a markdown report with:

```markdown
## Sprint PR Review Analysis

**Project:** {project_key}
**Analysis Date:** {date}

### Summary

| Metric | Value |
|--------|-------|
| Tickets in Review | {count} |
| PRs Found | {count} |
| Open | {count} |
| Approved & Ready | {count} |
| Changes Requested | {count} |
| Stale (>2 days) | {count} |

### Review Velocity

| Metric | Value |
|--------|-------|
| Avg Days Open (open PRs) | {days} days |
| Avg Time to First Review | {hours} hours |

### PRs Needing Attention

#### #{number} — {title}
- **Jira:** {issue_key}
- **Author:** {author}
- **Status:** {decision}
- **Open for:** {days} days
- **Last activity:** {days} days ago
- **Flags:** {flags}
- **Recommendation:** {action}

### All PRs

| PR | Jira | Author | Days Open | Reviews | Status | Flags |
|---|---|---|---|---|---|---|

### Recommendations

- Aggregated suggestions based on patterns observed
```

---

## Example Usage

**User:** "Check PR status for ACA sprint"

**Agent actions:**
1. Ask for board ID if not provided
2. Query Jira: `project = ACA AND sprint in openSprints() AND status = "Review"`
   - Include `customfield_10020` field for sprint/board data
3. Filter results by the specified board ID
4. Extract PR URLs from comments and descriptions
5. Fetch PR details via `gh pr view`
6. Generate report with metrics and recommendations

**User:** "Analyze PRs for ACA board 10910"

**Agent actions:**
1. Query Jira for ACA project with open sprints
2. Filter to board 10910 using `filter_by_board.py` or inline filtering
3. Extract and fetch PR details
4. Generate board-specific report

---

## Scripts

### Board Filtering Script

Location: `plugins/pr-review-analysis/scripts/filter_by_board.py`

Filters Jira data to only include tickets in sprints on a specific board:

```bash
# Filter Jira data by board ID
python filter_by_board.py --input jira.json --board {board_id} --output filtered.json

# Also extract PR URLs
python filter_by_board.py --input jira.json --board {board_id} --extract-prs

# Options
--board, -b    Jira board ID (required)
--status, -s   Status filter (default: Review)
--extract-prs  Also extract and output PR URLs
```

### Fetch GitHub PRs Script

Location: `plugins/pr-review-analysis/scripts/fetch_github_prs.py`

Fetches PR details from GitHub for a list of PR URLs:

```bash
# From a file of URLs
python fetch_github_prs.py --input pr_urls.txt --output prs.json

# From command line arguments
python fetch_github_prs.py --urls "https://github.com/org/repo/pull/1" "https://github.com/org/repo/pull/2"

# From stdin
cat pr_urls.txt | python fetch_github_prs.py > prs.json
```

### Report Generation Script

Location: `plugins/pr-review-analysis/scripts/generate_report.py`

```bash
# From separate files (with board filtering)
python generate_report.py --jira jira.json --prs prs.json --project ACA --board {board_id}

# Options
--project      Jira project key
--board        Jira board ID (required)
--sprint       Sprint name (optional)
--stale-days   Days to flag as stale (default: 2)
--output       Output file (default: stdout)
```
