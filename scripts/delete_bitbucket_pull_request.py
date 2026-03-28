#!/usr/bin/env python3
"""Delete a Bitbucket Server/Data Center pull request for a local instance.

Usage:
  python scripts/delete_bitbucket_pull_request.py <project> <repo> <pull_request_id>

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

from bitbucket_pull_request_api import delete_pull_request, load_script_credentials

PROJECT_KEY_HELP = "Bitbucket project key, for example PRJ"
REPO_SLUG_HELP = "Bitbucket repository slug"
PULL_REQUEST_ID_HELP = "Pull request id"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Delete a Bitbucket Server/DC pull request on http://localhost:7990."
    )
    parser.add_argument("project_key", help=PROJECT_KEY_HELP)
    parser.add_argument("repo_slug", help=REPO_SLUG_HELP)
    parser.add_argument("pull_request_id", type=int, help=PULL_REQUEST_ID_HELP)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    username, password = load_script_credentials()
    if not username or not password:
        parser.error("SE_USER and SE_PASSWORD must be set (or present in the repo .env file).")

    result = delete_pull_request(
        args.project_key,
        args.repo_slug,
        args.pull_request_id,
        username=username,
        password=password,
    )

    pr_id = result.get("id", args.pull_request_id)
    title = result.get("title", "")
    print(f"Deleted pull request #{pr_id}: {title}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
