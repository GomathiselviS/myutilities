---
description: Analyze PR review health for Jira tickets in review during the active sprint
argument-hint: "[jira-project-key] --board BOARD_ID"
---

## Name

pr-review-analysis:analyze-sprint-prs

## Synopsis

```
/pr-review-analysis:analyze-sprint-prs [jira-project-key] [--board BOARD_ID]
```

## Description

Gathers pull requests from Jira tickets that are in review status during the active
sprint on a specific Jira board, then analyzes each PR for review health metrics including:

- **Review duration** — How long the PR has been open for review
- **Comment resolution** — Whether review comments have been addressed
- **Resolution time** — How long it took to address feedback
- **Reviewer engagement** — Number of reviews, approvals, and pending reviewers

This command requires AI reasoning to:
- Query Jira for tickets in the active sprint with review status
- Extract PR URLs from Jira comments, development panel, and remote links
- Fetch PR details from GitHub including reviews, comments, and approvals
- Calculate health metrics and identify PRs needing attention
- Generate actionable recommendations for improving review velocity

Review optional — this produces an analytical report for team awareness.

## Prerequisites

**Jira (Atlassian MCP)**

The Atlassian MCP plugin must be configured with valid credentials:
- `ATLASSIAN_API_TOKEN` — API token from https://id.atlassian.com/manage-profile/security/api-tokens
- `ATLASSIAN_EMAIL` — Email associated with the Atlassian account
- `ATLASSIAN_SITE_URL` — Your Jira instance URL (e.g., `https://yourcompany.atlassian.net`)

**GitHub**

One of the following:
- `gh` CLI authenticated — Run `gh auth login` once
- `GITHUB_TOKEN` environment variable — Personal access token with `repo` scope

## Implementation

### Phase 1: Load Context

1. Load skill: `plugins/pr-review-analysis/skills/analyze-sprint-prs/SKILL.md`

### Phase 2: Execute

#### Step 1: Identify the Jira Project

Determine the Jira project to query:

- If argument provided: Use the specified project key
- If no argument: Ask the user which Jira project to analyze, or attempt to
  detect from recent context

#### Step 2: Query Jira for Tickets in Review

Use the Jira MCP tools to find tickets:

1. Use `searchJiraIssuesUsingJql` with query:
   ```jql
   project = {project_key} AND sprint in openSprints() AND status = "Review"
   ```

   **Important:** Include the `customfield_10020` (Sprint) field to filter by board ID.

2. For each ticket found, retrieve:
   - Issue key, summary, assignee
   - Time in current status (from changelog if needed)
   - Git Pull Request field (`customfield_10875`) — primary PR source
   - All comments (scan for PR URLs)
   - Development info / remote links
   - Sprint field (`customfield_10020`) containing `boardId`

3. **Filter by Board ID:** Only include tickets where the sprint's `boardId` matches
   the specified board. Use the `filter_by_board.py` script:
   ```bash
   python plugins/pr-review-analysis/scripts/filter_by_board.py \
     --input jira_data.json \
     --board {board_id} \
     --output filtered_jira.json
   ```

4. If no tickets found with exact status match, try broader query:
   ```jql
   project = {project_key} AND sprint in openSprints()
   ```
   Then filter for statuses containing "review" (case-insensitive) and matching board ID.

#### Step 3: Extract PR URLs from Each Ticket

For each Jira ticket:

1. **From comments**: Use `getJiraIssue` to fetch issue details with comments.
   Scan comment bodies for PR URL patterns:
   - `https://github.com/{owner}/{repo}/pull/{number}`
   - `https://gitlab.com/{group}/{project}/-/merge_requests/{number}`
   - `https://bitbucket.org/{workspace}/{repo}/pull-requests/{number}`

2. **From remote links**: Use `getJiraIssueRemoteIssueLinks` to find linked PRs.

3. **From development panel**: If available via the Jira API, extract linked PRs.

4. Deduplicate PR URLs per ticket and across tickets.

#### Step 4: Fetch PR Details from GitHub

For each unique GitHub PR URL extracted:

1. Parse the URL to extract `owner`, `repo`, and `pull_number`.

2. Use `gh` CLI or GitHub API via `WebFetch` to retrieve:
   - PR metadata: state, created_at, updated_at, author, title, draft status
   - Reviews: reviewer, state (APPROVED, CHANGES_REQUESTED, COMMENTED), submitted_at
   - Review comments: body, created_at, resolved status, author
   - Requested reviewers: users/teams who haven't responded

3. If authentication is required and unavailable, report which PRs could not
   be analyzed and suggest the user authenticate with `gh auth login`.

#### Step 5: Calculate Metrics for Each PR

Apply the metrics from the `pr-analysis` skill:

1. **Review duration**: Days since PR was created
2. **Days since last activity**: Days since `updated_at`
3. **Total comments**: Count of review comments
4. **Unresolved threads**: Comments not marked resolved or without follow-up
5. **Average time to address**: For resolved comments, mean time between
   comment creation and resolution/response
6. **Reviewer response rate**: Reviews completed / reviews requested
7. **Approval status**: APPROVED, CHANGES_REQUESTED, PENDING, or CONFLICTING

#### Step 6: Identify PRs Needing Attention

Flag PRs based on these thresholds:

| Flag | Condition |
|------|-----------|
| STALE | No activity > 2 days |
| BLOCKED | Changes requested, no commits since |
| UNREVIEWED | Open > 2 days, no reviews |
| UNRESOLVED | Comments without response > 2 days |
| APPROVAL_PENDING | Approved by some, waiting on others |

#### Step 7: Generate Summary Statistics

Calculate sprint-level metrics:

- Total tickets in review
- Total PRs found
- PR count by approval status
- Average review duration
- Average time to first review
- Average comment resolution time
- Count of PRs needing attention by flag type

### Phase 3: Report

Use the report generation script to produce the final output:

```bash
python plugins/pr-review-analysis/scripts/generate_report.py \
  --jira jira_data.json \
  --prs pr_data.json \
  --project {project_key}
```

Or present the analysis manually using this format:

```markdown
## Sprint PR Review Analysis

**Project:** {project_key}
**Sprint:** {sprint_name}
**Analysis Date:** {date}

### Summary

| Metric | Value |
|--------|-------|
| Tickets in Review | {count} |
| PRs Found | {count} |
| Approved & Ready | {count} |
| Awaiting Review | {count} |
| Changes Requested | {count} |
| Stale (>2 days) | {count} |

### Review Velocity

| Metric | Value |
|--------|-------|
| Avg Review Duration | {days} days |
| Avg Time to First Review | {hours} hours |
| Avg Comment Resolution Time | {hours} hours |
| Reviewer Response Rate | {percent}% |

### PRs Needing Attention

{For each flagged PR:}

#### {repo}#{number} — {title}
- **Jira:** {issue_key}
- **Author:** {author}
- **Status:** {approval_status}
- **Open for:** {days} days
- **Last activity:** {days} days ago
- **Flags:** {flags}
- **Unresolved comments:** {count}
- **Recommendation:** {specific action to unblock}

### All PRs in Review

| PR | Jira | Author | Days Open | Reviews | Status | Flags |
|----|------|--------|-----------|---------|--------|-------|
| {repo}#{number} | {key} | {author} | {days} | {completed}/{requested} | {status} | {flags} |
...

### Recommendations

{Aggregated recommendations based on patterns observed:}
- If multiple PRs are stale: "Consider a team review session to clear the backlog"
- If reviewers are unresponsive: "Redistribute review load or set review SLAs"
- If comments go unaddressed: "Establish expectation for comment response within X hours"

---
*Generated by AI (pr-review-analysis:analyze-sprint-prs) — verify PR states
directly in GitHub before taking action.*
```

## Examples

1. **Analyze a specific project:**
   ```
   /pr-review-analysis:analyze-sprint-prs AAP
   ```
   Queries Jira project AAP for tickets in review in the active sprint,
   extracts linked PRs, and generates a health report.

2. **Analyze without specifying project (triggers prompt):**
   ```
   /pr-review-analysis:analyze-sprint-prs
   ```
   Asks which Jira project to analyze.

3. **Typical output for a PR needing attention:**
   ```
   #### ansible/ansible-core#12345 — Fix module argument validation
   - Jira: AAP-1234
   - Author: developer1
   - Status: CHANGES_REQUESTED
   - Open for: 7 days
   - Last activity: 4 days ago
   - Flags: STALE, BLOCKED
   - Unresolved comments: 3
   - Recommendation: Author needs to address the 3 unresolved comments
     from reviewer2. Consider pinging in Slack or the PR.
   ```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `$1` — jira-project-key | No | Jira project key (e.g., AAP, AWX). If omitted, prompts for input. |
| `--board BOARD_ID` | **Yes** | Jira board ID to filter tickets. Required. |

## Return Value

- **Markdown**: Structured PR review health report with sprint summary,
  velocity metrics, flagged PRs with recommendations, and a full PR table.
