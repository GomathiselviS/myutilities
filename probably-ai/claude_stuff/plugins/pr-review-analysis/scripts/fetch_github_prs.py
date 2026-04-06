#!/usr/bin/env python3
"""
Fetch GitHub PR Details

Fetches PR details from GitHub for a list of PR URLs using the gh CLI.

Usage:
    python fetch_github_prs.py --input pr_urls.txt --output prs.json
    python fetch_github_prs.py --urls "https://github.com/org/repo/pull/1" "https://github.com/org/repo/pull/2"

    Or pipe URLs (one per line):
    cat pr_urls.txt | python fetch_github_prs.py > prs.json

Output:
    JSON array of PR objects with: number, title, state, createdAt, updatedAt,
    author, reviewDecision, reviews, isDraft, url
"""

import argparse
import json
import re
import subprocess
import sys
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch GitHub PR details")
    parser.add_argument("--input", "-i", type=str, help="File with PR URLs (one per line)")
    parser.add_argument("--output", "-o", type=str, help="Output JSON file (default: stdout)")
    parser.add_argument("--urls", nargs="*", help="PR URLs as arguments")
    return parser.parse_args()


def load_pr_urls(args: argparse.Namespace) -> list[str]:
    """Load PR URLs from file, arguments, or stdin."""
    urls: list[str] = []

    if args.urls:
        urls.extend(args.urls)

    if args.input:
        with open(args.input) as f:
            urls.extend(line.strip() for line in f if line.strip())

    if not urls and not sys.stdin.isatty():
        urls.extend(line.strip() for line in sys.stdin if line.strip())

    return urls


def parse_pr_url(url: str) -> tuple[str, int] | None:
    """Parse a GitHub PR URL into (owner/repo, number)."""
    match = re.match(r"https://github\.com/([^/]+/[^/]+)/pull/(\d+)", url)
    if match:
        return match.group(1), int(match.group(2))
    return None


def fetch_pr_details(repo: str, number: int) -> dict[str, Any]:
    """Fetch PR details using gh CLI."""
    fields = [
        "number",
        "title",
        "state",
        "createdAt",
        "updatedAt",
        "author",
        "reviewDecision",
        "reviews",
        "isDraft",
        "url",
    ]

    try:
        result = subprocess.run(
            ["gh", "pr", "view", str(number), "-R", repo, "--json", ",".join(fields)],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        return {
            "error": f"Failed to fetch {repo}#{number}: {e.stderr.strip()}",
            "url": f"https://github.com/{repo}/pull/{number}",
        }
    except json.JSONDecodeError:
        return {
            "error": f"Invalid JSON response for {repo}#{number}",
            "url": f"https://github.com/{repo}/pull/{number}",
        }


def main() -> None:
    args = parse_args()
    urls = load_pr_urls(args)

    if not urls:
        print("Error: No PR URLs provided", file=sys.stderr)
        print("Usage: python fetch_github_prs.py --input urls.txt", file=sys.stderr)
        print("   or: python fetch_github_prs.py --urls URL1 URL2", file=sys.stderr)
        print("   or: echo URL | python fetch_github_prs.py", file=sys.stderr)
        sys.exit(1)

    # Deduplicate and parse URLs
    seen: set[str] = set()
    pr_refs: list[tuple[str, int]] = []

    for url in urls:
        if url in seen:
            continue
        seen.add(url)

        parsed = parse_pr_url(url)
        if parsed:
            pr_refs.append(parsed)
        else:
            print(f"Warning: Invalid PR URL: {url}", file=sys.stderr)

    # Fetch PR details
    print(f"Fetching {len(pr_refs)} PRs...", file=sys.stderr)
    prs: list[dict[str, Any]] = []

    for repo, number in pr_refs:
        pr = fetch_pr_details(repo, number)
        prs.append(pr)
        if "error" in pr:
            print(f"  Error: {pr['error']}", file=sys.stderr)
        else:
            print(f"  Fetched: {repo}#{number}", file=sys.stderr)

    # Output
    output_json = json.dumps(prs, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_json)
        print(f"Wrote {len(prs)} PRs to {args.output}", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
