"""Read-only client for the remote RTX media queue.

The client only permits HTTPS endpoints resolving to globally routable addresses.
Redirects are not followed, preventing a configured endpoint from redirecting
requests into private network services. Only documented read endpoints are used.
"""
from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urljoin, urlparse

import requests


class RTXError(RuntimeError):
    """Raised when the RTX service cannot be queried safely."""


def _validate_base_url(base_url: str) -> str:
    value = str(base_url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise RTXError("RTX base URL must be a valid HTTPS URL.")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise RTXError("RTX URL credentials and non-standard ports are not allowed.")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in ("localhost",) or hostname.endswith((".localhost", ".local")):
        raise RTXError("Local and .local RTX addresses are not allowed from the hosted app.")
    try:
        addresses = {ipaddress.ip_address(hostname)}
    except ValueError:
        try:
            records = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
            addresses = {ipaddress.ip_address(record[4][0]) for record in records}
        except (OSError, ValueError) as exc:
            raise RTXError("RTX hostname could not be resolved to a public address.") from exc
    if not addresses or any(not address.is_global for address in addresses):
        raise RTXError("RTX hostname must resolve only to globally routable public IP addresses.")
    return value.rstrip("/")


def _endpoint(base_url: str, path: str) -> str:
    base = _validate_base_url(base_url) + "/"
    return urljoin(base, path.lstrip("/"))


def _headers(
    api_token: str = "",
    access_client_id: str = "",
    access_client_secret: str = "",
) -> dict[str, str]:
    headers = {"Accept": "application/json, text/html;q=0.9, */*;q=0.8"}
    if api_token.strip():
        headers["Authorization"] = f"Bearer {api_token.strip()}"
    if access_client_id.strip() and access_client_secret.strip():
        headers["CF-Access-Client-Id"] = access_client_id.strip()
        headers["CF-Access-Client-Secret"] = access_client_secret.strip()
    return headers


def check_rtx(
    base_url: str, api_token: str = "", timeout: int = 8,
    access_client_id: str = "", access_client_secret: str = "",
) -> dict[str, Any]:
    """Check the documented queue homepage and images listing."""
    safe_base = _validate_base_url(base_url)
    result: dict[str, Any] = {"base_url": safe_base, "checks": []}
    for label, path in (("Queue homepage", "/"), ("Images endpoint", "/images?limit=1")):
        try:
            response = requests.get(
                _endpoint(safe_base, path),
                headers=_headers(api_token, access_client_id, access_client_secret),
                timeout=timeout,
                allow_redirects=False,
            )
            ok = 200 <= response.status_code < 300
            detail = "Responded successfully" if ok else response.text[:240]
            if label == "Images endpoint" and ok:
                content_type = response.headers.get("content-type", "").lower()
                if "json" not in content_type:
                    ok = False
                    detail = "Endpoint responded, but did not declare a JSON content type."
            result["checks"].append({
                "name": label, "ok": ok, "status": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "detail": detail,
            })
        except requests.RequestException as exc:
            result["checks"].append({
                "name": label, "ok": False, "status": None,
                "content_type": "", "detail": str(exc)[:240],
            })
    result["ok"] = all(item["ok"] for item in result["checks"])
    return result


def list_images(
    base_url: str,
    api_token: str = "",
    owner: str = "",
    limit: int = 20,
    timeout: int = 15,
    access_client_id: str = "",
    access_client_secret: str = "",
) -> Any:
    """Read the documented /images endpoint; never submits or changes jobs."""
    params: dict[str, Any] = {"limit": max(1, min(int(limit), 100))}
    if owner.strip():
        params["owner"] = owner.strip()
    try:
        response = requests.get(
            _endpoint(base_url, "/images"),
            params=params,
            headers=_headers(api_token, access_client_id, access_client_secret),
            timeout=timeout,
            allow_redirects=False,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RTXError(f"Could not retrieve RTX images: {exc}") from exc
    try:
        return response.json()
    except ValueError as exc:
        raise RTXError("RTX /images endpoint did not return valid JSON.") from exc
