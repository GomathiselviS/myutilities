---
description: List and prioritize epics from a Jira backlog board
argument-hint: "[--reorder KEY1 KEY2 ...]"
---

## Name

backlog-management:list-aca-epics

## Synopsis

```
/backlog-management:list-aca-epics
/backlog-management:list-aca-epics --reorder AAP-123 ACA-456
```

## Description

Lists backlog epics from Jira that have unsprinted child tickets, allowing you to
prioritize which epics should be at the top of the backlog. When reordering, moves
the child tickets (not the epics themselves) to the top of the backlog.

This command requires AI reasoning to:
- Present the backlog in a readable format
- Help the user decide which epics to prioritize
- Confirm actions before modifying Jira

## Implementation

### Phase 1: Load Context

1. Load skill: `plugins/backlog-management/skills/list-aca-epics/SKILL.md`

### Phase 2: Execute

Follow the instructions in the loaded skill to:

1. Run the list command to display current backlog epics
2. Ask the user which epics they want to prioritize
3. Run the reorder command with their selected epic keys

### Phase 3: Output

Display the results of each operation clearly, including:
- The full table of backlog epics
- Confirmation of any reordering actions taken
- Summary of tickets moved

## Examples

1. **List current backlog:**
   ```
   /backlog-management:list-aca-epics
   ```
   Displays all backlog epics with unsprinted children.

2. **Reorder with specific priorities:**
   ```
   /backlog-management:list-aca-epics --reorder AAP-123 ACA-456 AAP-789
   ```
   Moves child tickets of those epics to the top of the backlog.

## Arguments

| Argument | Required | Description |
|---|---|---|
| `--reorder` | No | Epic keys in priority order (highest first) |

## Return Value

- **Markdown**: Table of backlog epics and/or confirmation of reorder actions.
