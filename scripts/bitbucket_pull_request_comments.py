#!/usr/bin/env python3
"""List or delete Bitbucket Server/Data Center pull request comments for a local instance.

Usage:
  python scripts/bitbucket_pull_request_comments.py list <project> <repo> <pull_request_id>
  python scripts/bitbucket_pull_request_comments.py delete <project> <repo> <pull_request_id> <comment_id>

Authentication:
  SE_USER and SE_PASSWORD are read from the environment; for local repo usage
  this script also auto-loads the repo-root .env when present.

Bitbucket base URL is assumed to be http://localhost:7990 and this script targets
the REST API base at http://localhost:7990/rest/api/1.0.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from bitbucket_pull_request_api import (
    delete_pull_request_comment,
    list_pull_request_comments,
    load_script_credentials,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="List or delete Bitbucket Server/DC pull request comments on http://localhost:7990."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List comments for a pull request")
    list_parser.add_argument("project_key", help="Bitbucket project key, for example PRJ")
    list_parser.add_argument("repo_slug", help="Bitbucket repository slug")
    list_parser.add_argument("pull_request_id", type=int, help="Pull request id")

    delete_parser = subparsers.add_parser("delete", help="Delete one pull request comment by id")
    delete_parser.add_argument("project_key", help="Bitbucket project key, for example PRJ")
    delete_parser.add_argument("repo_slug", help="Bitbucket repository slug")
    delete_parser.add_argument("pull_request_id", type=int, help="Pull request id")
    delete_parser.add_argument("comment_id", type=int, help="Pull request comment id")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    username, password = load_script_credentials()
    if not username or not password:
        parser.error("SE_USER and SE_PASSWORD must be set (or present in the repo .env file).")

    if args.command == "list":
        comments = list_pull_request_comments(
            args.project_key,
            args.repo_slug,
            args.pull_request_id,
            username=username,
            password=password,
        )
        print(json.dumps(comments, indent=2))
        return 0

    comment = delete_pull_request_comment(
        args.project_key,
        args.repo_slug,
        args.pull_request_id,
        args.comment_id,
        username=username,
        password=password,
    )
    print(f"Deleted comment #{comment.get('id', args.comment_id)} from pull request #{args.pull_request_id}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
