---
name: backlog-prioritization
description: Knowledge for querying Jira backlogs — finding epics with unsprinted children and Agile API patterns for reordering tickets.
---

# Backlog Management

This skill provides patterns for querying and reordering Jira backlogs.

## On Invocation

When this skill is invoked, present the following capabilities:

```
**Backlog Prioritization** — What I can help with:

| Capability | Description |
|------------|-------------|
| **Query epics** | Find open epics by project, workstream, or component (natural language or JQL) |
| **Find unsprinted work** | Identify epics with tickets not yet assigned to a sprint |
| **Surface insights** | Flag blockers, approaching deadlines, stale epics, and cross-workstream dependencies |
| **Reorder backlog** | Move tickets to prioritize specific work (always with confirmation) |
| **Track decisions** | Log prioritization rationale and detect patterns over time |
| **Analyze blockers** | Cross-workstream blocker and dependency analysis |

**Example queries:**
- "Show me unfinished epics for Cloud Content"
- "Which epics have unsprinted children?"
- "What's blocking the 2.6 release?"
- "Bump AAP-12345 to top of the backlog"

What would you like to do?
```

## Querying Backlog Epics

### Find Open Epics

**Basic query (all epics):**
```
project = $PROJECT AND issuetype = Epic AND statusCategory != Done ORDER BY Rank
```

**Filter by workstream:**
```
project = $PROJECT AND issuetype = Epic AND "Workstream" = "$WORKSTREAM" AND statusCategory != Done ORDER BY Rank
```

**Filter by component:**
```
project = $PROJECT AND issuetype = Epic AND component = $COMPONENT AND ("Workstream" = "$WORKSTREAM" OR "Workstream" is EMPTY) AND statusCategory != Done ORDER BY Rank
```

> **Important:** Always combine component filtering with a Workstream clause. Epics in AAP often have multiple components (e.g., an epic tagged controller, aap-gateway, and platform-operator). Filtering by component alone will include cross-team epics that happen to list your component.

Request fields: `key`, `summary`, `status`, `assignee`, `Workstream`

Note: "Workstream" is a custom field. Use exact value matching with quotes around the workstream name (e.g., `"Workstream" = "Cloud Content"`).

### Find Unsprinted Children

For each epic, check if it has tickets not yet assigned to a sprint:

```
"Parent" = $EPIC_KEY AND Sprint is EMPTY ORDER BY Rank
```

Only include epics in the result set if they have at least one unsprinted child.

## Presenting Results

Use the report generation script to format results:

```bash
python plugins/backlog-management/scripts/generate_backlog_report.py results.json --project AAP
```

Or pipe JSON directly:

```bash
cat results.json | python plugins/backlog-management/scripts/generate_backlog_report.py - -p AAP
```

Output format:

```markdown
## AAP Project (2 epics)

| # | Epic | Summary | Status | Unsprinted | Assignee |
|---|------|---------|--------|------------|----------|
| 1 | AAP-12345 | Vault KV v2 secrets engine support | In Progress | 3 ⚠️ | Cloud Content |
| 2 | AAP-12400 | amazon.aws EC2 inventory pagination | Backlog | 5 | Unassigned |
```

Flag "In Progress" epics that still have unsprinted children with ⚠️ — these represent active work without a full sprint plan. During prioritization, recommend scheduling these tickets first to unblock in-flight work.

## Reordering Tickets

> **Note:** The Atlassian MCP tools do not support the Jira Agile ranking API. Use the `reorder_backlog.py` script to perform ranking operations.

### Find Backlog Anchor

Get the current top of the unsprinted backlog:

```
project = $PROJECT AND Sprint is EMPTY ORDER BY Rank ASC
```

Use the first result as the initial anchor for ranking operations.

### Reorder Script

Use the reorder script to move tickets:

```bash
export JIRA_USER="your-email@company.com"
export JIRA_TOKEN="your-api-token"
python plugins/backlog-management/scripts/reorder_backlog.py \
  --tickets ACA-5383 ACA-5378 ACA-5379 \
  --anchor ACA-5327
```

**Required environment variables:**
- `JIRA_USER`: Your Atlassian account email
- `JIRA_TOKEN`: Atlassian API token (generate at https://id.atlassian.com/manage-profile/security/api-tokens)

**Security:** Never output `JIRA_TOKEN` values to stdout, logs, or confirmation messages. When displaying commands for user confirmation, redact the token value (e.g., `JIRA_TOKEN=***`).

Options:
- `--tickets` / `-t`: Ticket keys in priority order (highest first)
- `--anchor` / `-a`: Current top of backlog (tickets move before this)
- `--base-url` / `-u`: Jira URL (default: `$JIRA_BASE_URL` or `https://redhat.atlassian.net`)
- `--dry-run` / `-n`: Preview changes without modifying Jira

### Ranking API (Reference)

The script uses the Jira Agile API endpoint:

```
PUT /rest/agile/1.0/issue/rank
{
  "issues": ["TICKET-KEY"],
  "rankBeforeIssue": "ANCHOR-KEY"
}
```

### Reorder Algorithm

The script processes tickets in **reverse** order so the final ranking matches the input order:

1. Collect all unsprinted children for each priority epic (in priority order)
2. Get the initial anchor (current top of backlog)
3. Process tickets in reverse:
   - Move the ticket to rank before the anchor
   - Update anchor to the just-moved ticket

### Example

```bash
python reorder_backlog.py --tickets ACA-101 ACA-102 ACA-201 --anchor ACA-999
```

Processing (reverse order):
1. Move ACA-201 before ACA-999 → anchor = ACA-201
2. Move ACA-102 before ACA-201 → anchor = ACA-102
3. Move ACA-101 before ACA-102 → anchor = ACA-101

Final order: ACA-101, ACA-102, ACA-201, ACA-999, ...

## Confirmation Pattern

Before modifying the backlog, confirm with the user:

```
I'll move the following tickets to the top of the backlog:

**AAP-12345: Vault KV v2 secrets engine support** (2 tickets)
- AAP-12346
- AAP-12347

**AAP-12400: amazon.aws EC2 inventory pagination** (1 ticket)
- AAP-12401

Proceed? (yes/no)
```

## Error Handling

- If an epic has no unsprinted children, skip it and inform the user
- If the ranking API fails for a ticket, log the error and continue with remaining tickets
- Report final counts: "Moved X of Y tickets successfully"

## AI-Native Workflow

An enhanced workflow that captures prioritization context and surfaces cross-functional insights.

### 1. Discovery via Conversation

Instead of requiring JQL syntax, accept natural language queries:

- "Show me unfinished epics for cloud content"
- "What's blocking the 2.6 release?"
- "Which epics have the most unsprinted children?"

AI translates to JQL, executes queries, and analyzes cross-epic dependencies before presenting results with insights:

```
Here are 8 epics with unsprinted children:

| # | Epic | Summary | Status | Unsprinted | Insight |
|---|------|---------|--------|------------|---------|
| 1 | AAP-12345 | Vault KV v2 secrets engine support | In Progress | 5 ⚠️ | Blocks AAP-12500; active work needs sprint plan |
| 2 | AAP-12400 | amazon.aws EC2 inventory pagination | Backlog | 3 | Approaching deadline (Apr 15) |
| 3 | AAP-12450 | Vault AppRole auth method | Backlog | 2 | No dependencies |

⚠️ AAP-12345 is In Progress with unsprinted children — recommend prioritizing these tickets first.
```

### 2. Contextual Prioritization

When the user selects epics to prioritize, capture the reasoning:

```
User: Bump AAP-12345 to top

AI: What's driving this priority?
    1. Customer commitment
    2. Technical dependency/blocker
    3. Sprint deadline
    4. Other (please specify)

User: Vault KV v2 is blocking the amazon.aws credential lookup

AI: Got it — prioritizing AAP-12345 as blocker for amazon.aws integration.
    [Stores context on epic or in local knowledge base]
```

This creates queryable institutional knowledge about prioritization rationale.

### 3. Execution with Confirmation

Present the planned reordering with clear rationale:

```
I'll move the following tickets to the top of the backlog:

**AAP-12345: Vault KV v2 secrets engine support** (5 tickets) — blocker for amazon.aws
- AAP-12346, AAP-12347, AAP-12348, AAP-12349, AAP-12350

**AAP-12400: amazon.aws EC2 inventory pagination** (3 tickets) — deadline Apr 15
- AAP-12401, AAP-12402, AAP-12403

Proceed? (yes/no)
```

### 4. Pattern Detection Over Time

After multiple prioritization sessions, surface patterns:

- "You've prioritized Vault-related work 6 times this quarter. Consider a recurring 'secrets management' sprint placeholder."
- "AAP-12600 (S3 lifecycle rules) has been deprioritized in 3 consecutive sessions. Should it be moved to icebox?"
- "3 epics across amazon.aws and community.hashi_vault are blocked by AAP-12345. Consider prioritizing it first."

### 5. Cross-Workstream Insights

Automatically surface cross-team dependencies without requiring manual JQL:

```
Cross-workstream analysis for AAP:

Blockers affecting multiple collections:
- AAP-12345 (Vault KV v2) blocks 4 epics across amazon.aws and community.hashi_vault

Unassigned epics by collection:
- amazon.aws: 2 unassigned
- community.hashi_vault: 1 unassigned

Epics with no activity in 30+ days:
- AAP-12600 (S3 lifecycle rules), AAP-12700 (Vault transit engine) — consider archiving or re-scoping
```

### Supporting Scripts

#### Prioritization History

Track decisions and detect patterns using `prioritization_history.py`:

```bash
# Log a decision with context
python plugins/backlog-management/scripts/prioritization_history.py log \
  --epic AAP-12345 \
  --reason technical-dependency \
  --note "Vault KV v2 blocking amazon.aws credential lookup"

# View recent history
python plugins/backlog-management/scripts/prioritization_history.py show --limit 10

# Detect patterns across sessions
python plugins/backlog-management/scripts/prioritization_history.py patterns

# Find epics that keep getting reprioritized (may be stuck)
python plugins/backlog-management/scripts/prioritization_history.py stale
```

Reason types: `customer-commitment`, `technical-dependency`, `sprint-deadline`, `blocker`, `executive-request`, `other`

#### Cross-Workstream Analysis

Analyze blockers and dependencies using `analyze_blockers.py`:

```bash
# From a Jira export file
python plugins/backlog-management/scripts/analyze_blockers.py epics.json

# Output raw JSON for further processing
python plugins/backlog-management/scripts/analyze_blockers.py epics.json --json
```

The script identifies:
- High-impact blockers (issues blocking 2+ epics)
- Cross-workstream blockers (affecting multiple teams)
- Unassigned epics by workstream

### Implementation Notes

- Conversational input translates *to* JQL, not replaces it — query patterns remain the foundation
- Context capture is stored locally in `~/.backlog-prioritization-history.json`
- Pattern detection requires at least 5 logged decisions to generate insights
- Human confirmation before modifying Jira remains mandatory — this is oversight, not a bottleneck
