"""CLI entry point for the code review agent."""

import os

import typer

from code_review.runner import run_review

app = typer.Typer()


@app.command()
def review(
    owner: str = typer.Option(
        None,
        "--owner",
        "-o",
        help="Repo owner (or set SCM_OWNER)",
    ),
    repo: str = typer.Option(
        None,
        "--repo",
        "-r",
        help="Repo name (or set SCM_REPO)",
    ),
    pr: int = typer.Option(
        None,
        "--pr",
        "-p",
        help="PR number (or set SCM_PR_NUM)",
    ),
    head_sha: str = typer.Option(
        "",
        "--head-sha",
        help="Head commit SHA (or set SCM_HEAD_SHA)",
    ),
) -> None:
    """Run the code review agent on a pull request."""
    owner = owner or os.environ.get("SCM_OWNER", "")
    repo = repo or os.environ.get("SCM_REPO", "")
    pr_num = pr if pr is not None else _parse_int(os.environ.get("SCM_PR_NUM", ""))
    head_sha_val = head_sha or os.environ.get("SCM_HEAD_SHA", "")

    if not owner or not repo or pr_num is None:
        typer.echo(
            "Error: owner, repo, and pr are required (--owner, --repo, --pr or SCM_* env vars)",
            err=True,
        )
        raise typer.Exit(1)

    run_review(owner=owner, repo=repo, pr_number=pr_num, head_sha=head_sha_val)


def _parse_int(s: str) -> int | None:
    try:
        return int(s) if s else None
    except ValueError:
        return None


if __name__ == "__main__":
    app()
