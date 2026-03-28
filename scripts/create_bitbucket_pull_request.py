#!/usr/bin/env python3
"""Create a Bitbucket Server/Data Center pull request for a local instance.

Usage:
  python scripts/create_bitbucket_pull_request.py <project> <repo> <source_branch> <destination_branch>

Authentication:
  SE_USER and SE_PASSWORD are read from the environment; for local repo usage
  this script also auto-loads the repo-root .env when present.

Bitbucket base URL is assumed to be http://localhost:7990 and this script targets
the REST API base at http://localhost:7990/rest/api/1.0.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from bitbucket_pull_request_api import (
    branch_ref,
    build_pr_payload,
    create_pull_request,
    extract_pull_request_url,
    load_script_credentials,
)

PROJECT_KEY_HELP = "Bitbucket project key, for example PRJ"
REPO_SLUG_HELP = "Bitbucket repository slug"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a Bitbucket Server/DC pull request on http://localhost:7990."
    )
    parser.add_argument("project_key", help=PROJECT_KEY_HELP)
    parser.add_argument("repo_slug", help=REPO_SLUG_HELP)
    parser.add_argument("source_branch", help="Source branch name")
    parser.add_argument("destination_branch", help="Destination branch name")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    username, password = load_script_credentials()
    if not username or not password:
        parser.error("SE_USER and SE_PASSWORD must be set (or present in the repo .env file).")

    result = create_pull_request(
        args.project_key,
        args.repo_slug,
        args.source_branch,
        args.destination_branch,
        username=username,
        password=password,
    )

    pr_id = result.get("id", "<unknown>")
    title = result.get("title", "")
    pr_url = extract_pull_request_url(result)

    print(f"Created pull request #{pr_id}: {title}")
    if pr_url:
        print(pr_url)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
