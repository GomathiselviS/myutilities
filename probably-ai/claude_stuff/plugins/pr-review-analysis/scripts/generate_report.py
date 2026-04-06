#!/usr/bin/env python3
"""
Generate PR Review Analysis Report

Reads Jira ticket data and GitHub PR data, then generates a markdown report
analyzing PR review health for the active sprint.

Usage:
    python generate_report.py --jira <jira_data.json> --prs <pr_data.json> [options]

    Or pipe data via stdin:
    cat combined_data.json | python generate_report.py --stdin

Input formats:
    --jira: Jira API response with issues array
    --prs:  Array of GitHub PR objects (from gh pr view --json)
    --stdin: Combined JSON with "jira" and "prs" keys

Output:
    Markdown report to stdout (or file with --output)
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate PR Review Analysis Report")
    parser.add_argument("--jira", type=str, help="Path to Jira data JSON file")
    parser.add_argument("--prs", type=str, help="Path to GitHub PR data JSON file")
    parser.add_argument("--stdin", action="store_true", help="Read combined JSON from stdin")
    parser.add_argument("--project", type=str, default="", help="Jira project key")
    parser.add_argument("--sprint", type=str, default="", help="Sprint name")
    parser.add_argument("--board", type=int, required=True, help="Jira board ID to filter (required)")
    parser.add_argument("--output", "-o", type=str, help="Output file (default: stdout)")
    parser.add_argument("--stale-days", type=int, default=2, help="Days without activity to flag as stale")
    parser.add_argument("--unreviewed-days", type=int, default=2, help="Days without review to flag")
    return parser.parse_args()


def load_data(args: argparse.Namespace) -> tuple[dict, list]:
    """Load Jira and PR data from files or stdin."""
    if args.stdin:
        data = json.load(sys.stdin)
        return data.get("jira", {}), data.get("prs", [])

    jira_data = {}
    pr_data = []

    if args.jira:
        with open(args.jira) as f:
            jira_data = json.load(f)

    if args.prs:
        with open(args.prs) as f:
            pr_data = json.load(f)

    return jira_data, pr_data


def filter_issues_by_board(issues: list, board_id: int) -> list:
    """Filter Jira issues to only those in sprints belonging to the specified board."""
    filtered = []
    for issue in issues:
        sprints = issue.get("fields", {}).get("customfield_10020", []) or []
        for sprint in sprints:
            if isinstance(sprint, dict) and sprint.get("boardId") == board_id and sprint.get("state") == "active":
                filtered.append(issue)
                break
    return filtered


def extract_pr_urls_from_adf(adf_content: dict | str | None) -> set[str]:
    """Extract PR URLs from Atlassian Document Format content."""
    pr_pattern = re.compile(r'https://github\.com/[^/]+/[^/]+/pull/\d+')
    prs: set[str] = set()

    if not adf_content:
        return prs

    if isinstance(adf_content, str):
        prs.update(pr_pattern.findall(adf_content))
        return prs

    # Handle ADF structure (dict with content array)
    def walk_adf(node: dict | list) -> None:
        if isinstance(node, dict):
            # Check for text content
            if node.get("type") == "text":
                text = node.get("text", "")
                prs.update(pr_pattern.findall(text))
            # Check for link marks
            for mark in node.get("marks", []):
                if mark.get("type") == "link":
                    href = mark.get("attrs", {}).get("href", "")
                    prs.update(pr_pattern.findall(href))
            # Recurse into content
            for child in node.get("content", []):
                walk_adf(child)
        elif isinstance(node, list):
            for item in node:
                walk_adf(item)

    walk_adf(adf_content)
    return prs


def extract_pr_urls(jira_data: dict, board_id: int | None = None) -> dict[str, list[str]]:
    """Extract PR URLs from Jira issues, mapping issue key to PR URLs."""
    pr_pattern = re.compile(
        r'https://github\.com/([^/]+/[^/]+)/pull/(\d+)'
        r'|https://gitlab\.com/([^/]+/[^/]+)/-/merge_requests/(\d+)'
        r'|https://bitbucket\.org/([^/]+/[^/]+)/pull-requests/(\d+)'
    )

    issue_prs: dict[str, list[str]] = {}

    issues = jira_data.get("issues", {}).get("nodes", [])
    if not issues:
        issues = jira_data.get("issues", [])

    # Filter by board if specified
    if board_id is not None:
        issues = filter_issues_by_board(issues, board_id)

    for issue in issues:
        key = issue.get("key", "")
        prs = set()
        fields = issue.get("fields", {})

        # Extract from Git Pull Request field (customfield_10875) - primary source
        git_pr_field = fields.get("customfield_10875")
        prs.update(extract_pr_urls_from_adf(git_pr_field))

        # Extract from comments
        comment_data = fields.get("comment", {})
        comments = comment_data.get("comments", []) if isinstance(comment_data, dict) else []

        for comment in comments:
            body = comment.get("body", "")
            if isinstance(body, str):
                for match in pr_pattern.finditer(body):
                    prs.add(match.group(0))

        # Extract from description
        description = fields.get("description", "")
        if isinstance(description, str):
            for match in pr_pattern.finditer(description):
                prs.add(match.group(0))

        if prs:
            issue_prs[key] = list(prs)

    return issue_prs


def parse_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string to datetime object."""
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


def analyze_pr(pr: dict, now: datetime, stale_days: int, unreviewed_days: int) -> dict[str, Any]:
    """Analyze a single PR and return metrics."""
    num = pr.get("number", 0)
    title = pr.get("title", "")[:60]
    author = pr.get("author", {}).get("login", "unknown")
    state = pr.get("state", "unknown")
    decision = pr.get("reviewDecision") or "PENDING"
    is_draft = pr.get("isDraft", False)
    url = pr.get("url", f"#{num}")

    created = parse_datetime(pr["createdAt"])
    updated = parse_datetime(pr["updatedAt"])
    days_open = (now - created).days
    days_since_update = (now - updated).days

    reviews = pr.get("reviews", [])
    review_count = len(reviews)
    approvals = sum(1 for r in reviews if r.get("state") == "APPROVED")
    changes_requested = sum(1 for r in reviews if r.get("state") == "CHANGES_REQUESTED")
    commented = sum(1 for r in reviews if r.get("state") == "COMMENTED")

    # Calculate time to first review
    time_to_first_review = None
    if reviews:
        review_dates = [parse_datetime(r["submittedAt"]) for r in reviews if r.get("submittedAt")]
        if review_dates:
            first_review = min(review_dates)
            time_to_first_review = (first_review - created).total_seconds() / 3600  # hours

    # Determine flags
    flags = []
    if state == "MERGED":
        flags.append("MERGED")
    elif state == "CLOSED":
        flags.append("CLOSED")
    else:
        if is_draft:
            flags.append("DRAFT")
        if decision == "APPROVED":
            flags.append("READY")
        if changes_requested > 0 and decision != "APPROVED":
            flags.append("BLOCKED")
        if days_since_update > stale_days:
            flags.append("STALE")
        if review_count == 0 and days_open > unreviewed_days and not is_draft:
            flags.append("UNREVIEWED")

    # Generate recommendation
    recommendation = None
    if "BLOCKED" in flags:
        recommendation = "Address the requested changes and request re-review"
    elif "STALE" in flags and "UNREVIEWED" in flags:
        recommendation = "Request reviewers — PR has had no reviews"
    elif "STALE" in flags:
        recommendation = "Follow up with reviewers or update the PR to signal activity"
    elif "UNREVIEWED" in flags:
        recommendation = "Request reviewers to begin the review process"
    elif "READY" in flags:
        recommendation = "Ready to merge — ensure CI passes and merge"

    return {
        "number": num,
        "title": title,
        "author": author,
        "url": url,
        "state": state,
        "decision": decision,
        "is_draft": is_draft,
        "days_open": days_open,
        "days_since_update": days_since_update,
        "review_count": review_count,
        "approvals": approvals,
        "changes_requested": changes_requested,
        "commented": commented,
        "time_to_first_review_hours": time_to_first_review,
        "flags": flags,
        "recommendation": recommendation,
    }


def extract_jira_tickets(jira_data: dict, board_id: int | None = None) -> list[dict]:
    """Extract ticket info from Jira data."""
    tickets = []
    issues = jira_data.get("issues", {}).get("nodes", [])
    if not issues:
        issues = jira_data.get("issues", [])

    # Filter by board if specified
    if board_id is not None:
        issues = filter_issues_by_board(issues, board_id)

    for issue in issues:
        key = issue.get("key", "")
        fields = issue.get("fields", {})
        summary = fields.get("summary", "")[:60]
        status = fields.get("status", {}).get("name", "")
        assignee = fields.get("assignee", {})
        assignee_name = assignee.get("displayName", "Unassigned") if assignee else "Unassigned"

        tickets.append({
            "key": key,
            "summary": summary,
            "status": status,
            "assignee": assignee_name,
        })

    return tickets


def generate_report(
    jira_data: dict,
    pr_data: list,
    project: str,
    sprint: str,
    board_id: int,
    stale_days: int,
    unreviewed_days: int,
) -> str:
    """Generate the markdown report."""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")

    # Extract Jira tickets (filtered by board)
    tickets = extract_jira_tickets(jira_data, board_id)
    issue_prs = extract_pr_urls(jira_data, board_id)

    # Build PR URL to Jira key mapping
    pr_to_jira: dict[int, list[str]] = {}
    for key, urls in issue_prs.items():
        for url in urls:
            match = re.search(r'/pull/(\d+)', url)
            if match:
                pr_num = int(match.group(1))
                pr_to_jira.setdefault(pr_num, []).append(key)

    # Analyze PRs
    analyzed_prs = []
    for pr in pr_data:
        if "error" in pr:
            continue
        analysis = analyze_pr(pr, now, stale_days, unreviewed_days)
        analysis["jira_keys"] = pr_to_jira.get(analysis["number"], [])
        analyzed_prs.append(analysis)

    # Calculate summary stats
    summary = {
        "total_tickets": len(tickets),
        "total_prs": len(analyzed_prs),
        "open": sum(1 for p in analyzed_prs if p["state"] == "OPEN"),
        "merged": sum(1 for p in analyzed_prs if p["state"] == "MERGED"),
        "approved": sum(1 for p in analyzed_prs if "READY" in p["flags"]),
        "changes_requested": sum(1 for p in analyzed_prs if "BLOCKED" in p["flags"]),
        "stale": sum(1 for p in analyzed_prs if "STALE" in p["flags"]),
        "unreviewed": sum(1 for p in analyzed_prs if "UNREVIEWED" in p["flags"]),
        "draft": sum(1 for p in analyzed_prs if "DRAFT" in p["flags"]),
    }

    # Calculate velocity metrics
    open_prs = [p for p in analyzed_prs if p["state"] == "OPEN"]
    avg_days_open = sum(p["days_open"] for p in open_prs) / len(open_prs) if open_prs else 0

    reviewed_prs = [p for p in analyzed_prs if p["time_to_first_review_hours"] is not None]
    avg_time_to_first_review = (
        sum(p["time_to_first_review_hours"] for p in reviewed_prs) / len(reviewed_prs)
        if reviewed_prs else None
    )

    # PRs needing attention (sorted by priority)
    attention_prs = [
        p for p in analyzed_prs
        if any(f in p["flags"] for f in ["STALE", "BLOCKED", "UNREVIEWED"])
        and p["state"] == "OPEN"
    ]
    attention_prs.sort(key=lambda x: (-len(x["flags"]), -x["days_open"]))

    # Build report
    lines = []
    lines.append("## Sprint PR Review Analysis\n")
    lines.append(f"**Project:** {project or 'N/A'}")
    lines.append(f"**Board:** {board_id}")
    if sprint:
        lines.append(f"**Sprint:** {sprint}")
    lines.append(f"**Analysis Date:** {date_str}")
    lines.append("")

    # Summary table
    lines.append("### Summary\n")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Tickets in Review | {summary['total_tickets']} |")
    lines.append(f"| PRs Found | {summary['total_prs']} |")
    lines.append(f"| Open | {summary['open']} |")
    lines.append(f"| Merged | {summary['merged']} |")
    lines.append(f"| Approved & Ready | {summary['approved']} |")
    lines.append(f"| Changes Requested | {summary['changes_requested']} |")
    lines.append(f"| Stale (>{stale_days} days) | {summary['stale']} |")
    lines.append(f"| Unreviewed (>{unreviewed_days} days) | {summary['unreviewed']} |")
    lines.append(f"| Draft | {summary['draft']} |")
    lines.append("")

    # Velocity metrics
    lines.append("### Review Velocity\n")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Avg Days Open (open PRs) | {avg_days_open:.1f} days |")
    if avg_time_to_first_review is not None:
        lines.append(f"| Avg Time to First Review | {avg_time_to_first_review:.1f} hours |")
    else:
        lines.append("| Avg Time to First Review | N/A |")
    lines.append("")

    # PRs needing attention
    if attention_prs:
        lines.append("### PRs Needing Attention\n")
        for p in attention_prs:
            jira_str = ", ".join(p["jira_keys"]) if p["jira_keys"] else "N/A"
            lines.append(f"#### #{p['number']} — {p['title']}")
            lines.append(f"- **Jira:** {jira_str}")
            lines.append(f"- **Author:** {p['author']}")
            lines.append(f"- **Status:** {p['decision']}")
            lines.append(f"- **Open for:** {p['days_open']} days")
            lines.append(f"- **Last activity:** {p['days_since_update']} days ago")
            lines.append(f"- **Flags:** {', '.join(p['flags'])}")
            if p["recommendation"]:
                lines.append(f"- **Recommendation:** {p['recommendation']}")
            lines.append("")

    # All PRs table
    lines.append("### All PRs\n")
    lines.append("| PR | Jira | Author | Days Open | Last Activity | Reviews | Status | Flags |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for p in sorted(analyzed_prs, key=lambda x: -x["days_open"]):
        jira_str = ", ".join(p["jira_keys"]) if p["jira_keys"] else "-"
        flags_str = ", ".join(p["flags"]) if p["flags"] else "-"
        reviews_str = f"{p['approvals']}A {p['changes_requested']}C"
        lines.append(
            f"| #{p['number']} | {jira_str} | {p['author']} | {p['days_open']}d | "
            f"{p['days_since_update']}d | {reviews_str} | {p['decision']} | {flags_str} |"
        )
    lines.append("")

    # Recommendations
    lines.append("### Recommendations\n")
    if summary["stale"] > 2:
        lines.append("- **Review backlog detected:** Consider a team review session to clear stale PRs")
    if summary["unreviewed"] > 0:
        lines.append("- **Unreviewed PRs:** Assign reviewers to PRs waiting for initial review")
    if summary["changes_requested"] > 2:
        lines.append("- **Blocked PRs:** Follow up with authors to address requested changes")
    if summary["approved"] > 0:
        lines.append(f"- **Ready to merge:** {summary['approved']} PR(s) approved and waiting for merge")
    if not any([summary["stale"] > 2, summary["unreviewed"], summary["changes_requested"] > 2]):
        lines.append("- Review process is healthy. No major issues detected.")
    lines.append("")

    # Footer
    lines.append("---")
    lines.append("*Generated by pr-review-analysis — verify PR states directly in GitHub before acting.*")

    return "\n".join(lines)


def main() -> None:
    args = parse_args()

    if not args.stdin and not (args.jira or args.prs):
        print("Error: Provide --jira and --prs files, or use --stdin", file=sys.stderr)
        sys.exit(1)

    jira_data, pr_data = load_data(args)

    report = generate_report(
        jira_data=jira_data,
        pr_data=pr_data,
        project=args.project,
        sprint=args.sprint,
        board_id=args.board,
        stale_days=args.stale_days,
        unreviewed_days=args.unreviewed_days,
    )

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
    else:
        print(report)


if __name__ == "__main__":
    main()
