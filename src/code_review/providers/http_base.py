"""Shared HTTP provider helpers for SCM adapters backed by httpx."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable, Iterator
from typing import Any, Literal

import httpx

from code_review.providers.base import FileInfo, ProviderInterface

PaginationMode = Literal["page", "next", "start"]
PageToken = str | int | None
FetchPage = Callable[[str, dict[str, Any] | None], Any]
NextPage = Callable[[Any, PageToken], PageToken]
RepeatHook = Callable[[PageToken], None]


class HttpXProvider(ProviderInterface):
    """Intermediate base class for SCM providers that talk to HTTP APIs via httpx."""

    _httpx_module = httpx

    def __init__(self, base_url: str, token: str, timeout: float = 30.0):
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout

    @abstractmethod
    def _auth_header(self) -> dict[str, str]:
        """Return auth headers for this provider."""

    def _default_headers(self) -> dict[str, str]:
        return {}

    def _headers(self) -> dict[str, str]:
        return {**self._default_headers(), **self._auth_header()}

    def _api_prefix(self) -> str:
        return ""

    def _build_url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        return f"{self._base_url}{self._api_prefix()}{path}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        request_headers = self._headers()
        if headers:
            request_headers = {**request_headers, **headers}
        request_kwargs: dict[str, Any] = {"headers": request_headers}
        if params:
            request_kwargs["params"] = params
        if json is not None:
            request_kwargs["json"] = json
        with self._httpx_module.Client(timeout=self._timeout) as client:
            response = getattr(client, method.lower())(self._build_url(path), **request_kwargs)
            response.raise_for_status()
            return response

    @staticmethod
    def _json_or_text_response(response: httpx.Response) -> Any:
        content_type = (response.headers.get("content-type") or "").lower()
        if "application/json" in content_type or "+json" in content_type:
            return response.json()
        return response.text

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._json_or_text_response(self._request("GET", path, params=params))

    def _get_text(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        return self._request("GET", path, params=params, headers=headers).text

    def _get_bytes(self, path: str, params: dict[str, Any] | None = None) -> bytes:
        return self._request("GET", path, params=params).content

    def _post(self, path: str, json: Any) -> Any:
        response = self._request("POST", path, json=json)
        return response.json() if response.content else None

    def _patch(self, path: str, json: Any) -> Any:
        response = self._request("PATCH", path, json=json)
        return response.json() if response.content else None

    def _put(self, path: str, json: Any) -> Any:
        response = self._request("PUT", path, json=json)
        return response.json() if response.content else None

    def _delete(self, path: str) -> None:
        self._request("DELETE", path)

    @staticmethod
    def _sha_guard_passes(base_sha: str, head_sha: str) -> bool:
        base = (base_sha or "").strip()
        head = (head_sha or "").strip()
        return bool(base and head and base != head)

    def _get_incremental_pr_diff(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        base_sha: str,
        head_sha: str,
    ) -> str:
        return super().get_incremental_pr_diff(owner, repo, pr_number, base_sha, head_sha)

    def get_incremental_pr_diff(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        base_sha: str,
        head_sha: str,
    ) -> str:
        if not self._sha_guard_passes(base_sha, head_sha):
            return self.get_pr_diff(owner, repo, pr_number)
        return self._get_incremental_pr_diff(owner, repo, pr_number, base_sha, head_sha)

    def _get_incremental_pr_files(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        base_sha: str,
        head_sha: str,
    ) -> list[FileInfo]:
        return super().get_incremental_pr_files(owner, repo, pr_number, base_sha, head_sha)

    def get_incremental_pr_files(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        base_sha: str,
        head_sha: str,
    ) -> list[FileInfo]:
        if not self._sha_guard_passes(base_sha, head_sha):
            return self.get_pr_files(owner, repo, pr_number)
        return self._get_incremental_pr_files(owner, repo, pr_number, base_sha, head_sha)

    @staticmethod
    def _next_page_url(data: Any, _current: PageToken = None) -> str | None:
        if not isinstance(data, dict):
            return None
        nxt = data.get("next")
        return nxt.strip() if isinstance(nxt, str) and nxt.strip() else None

    def _paginate_list(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        max_pages: int = 500,
        page_size: int | None = None,
        mode: PaginationMode = "next",
        initial_data: Any = None,
        fetch_page: FetchPage | None = None,
        next_page: NextPage | None = None,
        on_repeat: RepeatHook | None = None,
    ) -> Iterator[Any]:
        """Yield paginated API pages while centralizing page-token progression."""

        fetch = fetch_page or self._get
        current_path = path
        current_params = dict(params or {})
        current_token: PageToken

        if mode == "page":
            current_token = int(current_params.get("page", 1) or 1)
            current_params["page"] = current_token
            if page_size is not None:
                current_params.setdefault("per_page", page_size)
        elif mode == "start":
            current_token = int(current_params.get("start", 0) or 0)
            current_params["start"] = current_token
            if page_size is not None:
                current_params.setdefault("limit", page_size)
        else:
            current_token = current_path

        seen_tokens: set[str] = set()
        data = initial_data
        for _ in range(max_pages):
            if data is None:
                if mode == "next":
                    token_str = str(current_token)
                    if token_str in seen_tokens:
                        if on_repeat is not None:
                            on_repeat(current_token)
                        break
                    seen_tokens.add(token_str)
                    params_arg = dict(current_params) if current_params else None
                    data = fetch(current_path, params_arg)
                    current_params = {}
                else:
                    data = fetch(current_path, dict(current_params))

            yield data

            if mode == "page":
                if next_page is not None:
                    next_token = next_page(data, current_token)
                else:
                    if not isinstance(data, list) or page_size is None or len(data) < page_size:
                        break
                    next_token = int(current_token) + 1
                if next_token is None:
                    break
                if next_token == current_token:
                    if on_repeat is not None:
                        on_repeat(current_token)
                    break
                current_token = next_token
                current_params["page"] = current_token
            elif mode == "start":
                if next_page is None:
                    raise ValueError("start pagination requires a next_page callback")
                next_token = next_page(data, current_token)
                if next_token is None:
                    break
                if next_token == current_token:
                    if on_repeat is not None:
                        on_repeat(current_token)
                    break
                current_token = next_token
                current_params["start"] = current_token
            else:
                next_token = (
                    next_page(data, current_token)
                    if next_page is not None
                    else self._next_page_url(data)
                )
                if next_token is None:
                    break
                next_url = str(next_token).strip()
                if not next_url:
                    break
                current_path = next_url
                current_token = current_path

            data = None
