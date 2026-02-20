"""Gitea API provider."""

from typing import Any

import httpx

from code_review.providers.base import (
    FileInfo,
    ProviderInterface,
    ReviewComment,
)


class GiteaProvider(ProviderInterface):
    """Gitea API client for PR diff, file content, and review comments."""

    def __init__(self, base_url: str, token: str, timeout: float = 30.0):
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"token {self._token}",
            "Accept": "application/json",
        }

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self._base_url}/api/v1{path}"
        with httpx.Client(timeout=self._timeout) as client:
            r = client.get(url, headers=self._headers(), params=params)
            r.raise_for_status()
            return r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text

    def _get_text(self, path: str) -> str:
        url = f"{self._base_url}/api/v1{path}"
        with httpx.Client(timeout=self._timeout) as client:
            r = client.get(url, headers=self._headers())
            r.raise_for_status()
            return r.text

    def _post(self, path: str, json: Any) -> Any:
        url = f"{self._base_url}/api/v1{path}"
        with httpx.Client(timeout=self._timeout) as client:
            r = client.post(url, headers=self._headers(), json=json)
            r.raise_for_status()
            return r.json() if r.content else None

    def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Return unified diff for the PR."""
        path = f"/repos/{owner}/{repo}/pulls/{pr_number}.diff"
        return self._get_text(path)

    def get_file_content(self, owner: str, repo: str, ref: str, path: str) -> str:
        """Return file content at ref."""
        api_path = f"/repos/{owner}/{repo}/contents/{path}"
        resp = self._get(api_path, params={"ref": ref})
        if isinstance(resp, dict) and "content" in resp:
            import base64
            return base64.b64decode(resp["content"]).decode("utf-8", errors="replace")
        raise ValueError(f"Unexpected response for {path} at {ref}")

    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> list[FileInfo]:
        """Return list of changed files in the PR."""
        path = f"/repos/{owner}/{repo}/pulls/{pr_number}/files"
        data = self._get(path)
        if not isinstance(data, list):
            return []
        result: list[FileInfo] = []
        for f in data:
            status = f.get("status", "modified")
            result.append(
                FileInfo(
                    path=f.get("filename", f.get("path", "")),
                    status=status,
                    additions=f.get("additions", 0),
                    deletions=f.get("deletions", 0),
                )
            )
        return result

    def post_review_comments(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        comments: list[tuple[str, int, str]],
        head_sha: str = "",
    ) -> None:
        """Post inline review comments. Gitea CreatePullReview accepts comments array."""
        if not comments:
            return
        # Fetch PR to get head_sha if not provided
        if not head_sha:
            pr = self._get(f"/repos/{owner}/{repo}/pulls/{pr_number}")
            head_sha = pr.get("head", {}).get("sha", "")

        # Gitea CreatePullReview: body, event (APPROVE/REQUEST_CHANGES/COMMENT), comments
        # Each comment: path, body, line (1-based)
        review_comments = [
            {"path": path, "body": body, "line": line}
            for path, line, body in comments
        ]
        payload: dict[str, Any] = {
            "body": "Code review comments",
            "event": "COMMENT",
            "comments": review_comments,
        }
        self._post(f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews", payload)

    def get_existing_review_comments(
        self, owner: str, repo: str, pr_number: int
    ) -> list[ReviewComment]:
        """Return existing review comments. Gitea may not expose 'resolved' via API."""
        path = f"/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        data = self._get(path)
        if not isinstance(data, list):
            return []
        result: list[ReviewComment] = []
        for c in data:
            # Gitea PR comments: id, path, line, body; resolved status may be absent
            result.append(
                ReviewComment(
                    id=str(c.get("id", "")),
                    path=c.get("path", ""),
                    line=int(c.get("line", 0) or 0),
                    body=c.get("body", ""),
                    resolved=bool(c.get("resolved", False)),
                )
            )
        return result
