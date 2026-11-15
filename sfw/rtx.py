"""Read-only client for the remote RTX media queue.

Only documented read endpoints are used here. Job submission is intentionally
not implemented until the server's authenticated submission contract is known.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import requests


class RTXError(RuntimeError):
    """Raised when the RTX service cannot be queried safely."""


def _endpoint(base_url: str, path: str) -> str:
    base = base_url.strip().rstrip("/") + "/"
    return urljoin(base, path.lstrip("/"))


def _headers(api_token: str = "") -> dict[str, str]:
    headers = {"Accept": "application/json, text/html;q=0.9, */*;q=0.8"}
    if api_token.strip():
        headers["Authorization"] = f"Bearer {api_token.strip()}"
    return headers


def check_rtx(base_url: str, api_token: str = "", timeout: int = 8) -> dict[str, Any]:
    """Check the documented queue homepage and images listing."""
    if not base_url.strip().startswith(("https://", "http://")):
        raise RTXError("RTX base URL must start with https:// or http://.")
    result: dict[str, Any] = {"base_url": base_url.strip().rstrip("/"), "checks": []}
    for label, path in (("Queue homepage", "/"), ("Images endpoint", "/images?limit=1")):
        try:
            response = requests.get(
                _endpoint(base_url, path),
                headers=_headers(api_token),
                timeout=timeout,
                allow_redirects=True,
            )
            result["checks"].append({
                "name": label,
                "ok": 200 <= response.status_code < 300,
                "status": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "detail": "Responded successfully" if response.ok else response.text[:240],
            })
        except requests.RequestException as exc:
            result["checks"].append({
                "name": label,
                "ok": False,
                "status": None,
                "content_type": "",
                "detail": str(exc)[:240],
            })
    result["ok"] = all(item["ok"] for item in result["checks"])
    return result


def list_images(
    base_url: str,
    api_token: str = "",
    owner: str = "",
    limit: int = 20,
    timeout: int = 15,
) -> Any:
    """Read the documented /images endpoint; never submits or changes jobs."""
    if not base_url.strip().startswith(("https://", "http://")):
        raise RTXError("RTX base URL must start with https:// or http://.")
    params: dict[str, Any] = {"limit": max(1, min(int(limit), 100))}
    if owner.strip():
        params["owner"] = owner.strip()
    try:
        response = requests.get(
            _endpoint(base_url, "/images"),
            params=params,
            headers=_headers(api_token),
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RTXError(f"Could not retrieve RTX images: {exc}") from exc
    try:
        return response.json()
    except ValueError as exc:
        raise RTXError("RTX /images endpoint did not return valid JSON.") from exc
