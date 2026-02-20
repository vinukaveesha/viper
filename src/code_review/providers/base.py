"""Abstract provider interface for SCM backends (Gitea, GitLab, Bitbucket)."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """Metadata for a file in a PR."""

    path: str
    status: str = Field(default="modified", description="added, removed, modified")
    additions: int = 0
    deletions: int = 0


class ReviewComment(BaseModel):
    """A review comment with resolved status for fingerprinting."""

    id: str
    path: str
    line: int
    body: str
    resolved: bool = False


class ProviderInterface(ABC):
    """Abstract interface for SCM providers."""

    @abstractmethod
    def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Return unified diff string for the PR."""
        ...

    @abstractmethod
    def get_file_content(self, owner: str, repo: str, ref: str, path: str) -> str:
        """Return file content at ref (branch/tag/SHA)."""
        ...

    @abstractmethod
    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> list[FileInfo]:
        """Return list of changed files in the PR."""
        ...

    @abstractmethod
    def post_review_comments(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        comments: list[tuple[str, int, str]],
        head_sha: str = "",
    ) -> None:
        """Post inline comments. Each tuple is (path, line, body)."""
        ...

    @abstractmethod
    def get_existing_review_comments(
        self, owner: str, repo: str, pr_number: int
    ) -> list[ReviewComment]:
        """Return existing review comments (include resolved status for ignore list)."""
        ...
