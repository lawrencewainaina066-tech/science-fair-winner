"""Authenticated Supabase storage for private SFW research projects.

Every database operation uses the signed-in user's access token. Row-level
security in supabase/schema.sql is the actual isolation boundary; the anon key
is public configuration, never an admin/service-role credential.
"""
from urllib.parse import urlparse

import requests


class CloudStorageError(RuntimeError):
    """Safe, user-facing cloud storage error."""


def _settings():
    from .config import _setting

    base_url = _setting("SFW_SUPABASE_URL").rstrip("/")
    anon_key = _setting("SFW_SUPABASE_ANON_KEY")
    if not base_url or not anon_key:
        raise CloudStorageError(
            "Private cloud storage is not configured. Add SFW_SUPABASE_URL "
            "and SFW_SUPABASE_ANON_KEY in Streamlit Secrets."
        )
    parsed = urlparse(base_url)
    local = parsed.hostname in {"localhost", "127.0.0.1"}
    if parsed.scheme != "https" and not local:
        raise CloudStorageError("Supabase must use HTTPS outside local development.")
    if not parsed.netloc or parsed.username or parsed.password:
        raise CloudStorageError("The Supabase URL is invalid.")
    return base_url, anon_key


def _headers(anon_key, access_token=None, prefer=None):
    headers = {"apikey": anon_key, "Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _request(method, url, **kwargs):
    try:
        response = requests.request(method, url, timeout=20, **kwargs)
    except requests.RequestException as exc:
        raise CloudStorageError("Could not reach the private storage service. Check the connection and try again.") from exc
    if response.status_code >= 400:
        try:
            detail = response.json().get("msg") or response.json().get("message") or response.json().get("error_description")
        except (ValueError, AttributeError):
            detail = None
        if response.status_code in (401, 403):
            raise CloudStorageError("Your session is invalid or expired, or your account lacks permission. Sign in again.")
        raise CloudStorageError(str(detail or f"Cloud storage returned HTTP {response.status_code}.")[:400])
    if response.status_code == 204 or not response.content:
        return None
    try:
        return response.json()
    except ValueError as exc:
        raise CloudStorageError("The cloud service returned an unreadable response.") from exc


def sign_up(email, password):
    base, key = _settings()
    return _request(
        "POST", f"{base}/auth/v1/signup",
        headers=_headers(key), json={"email": email.strip(), "password": password},
    )


def sign_in(email, password):
    base, key = _settings()
    result = _request(
        "POST", f"{base}/auth/v1/token?grant_type=password",
        headers=_headers(key), json={"email": email.strip(), "password": password},
    )
    if not isinstance(result, dict) or not result.get("access_token"):
        raise CloudStorageError("Sign-in did not return an access token.")
    return result


def refresh_session(refresh_token):
    base, key = _settings()
    result = _request(
        "POST", f"{base}/auth/v1/token?grant_type=refresh_token",
        headers=_headers(key), json={"refresh_token": refresh_token},
    )
    if not isinstance(result, dict) or not result.get("access_token"):
        raise CloudStorageError("Your session could not be refreshed. Please sign in again.")
    return result


def _rest_url(table="sfw_projects"):
    base, _ = _settings()
    return f"{base}/rest/v1/{table}"


def save_project(access_token, title, payload):
    base, key = _settings()
    result = _request(
        "POST", f"{base}/rest/v1/sfw_projects",
        headers=_headers(key, access_token, "return=representation"),
        json={"title": str(title).strip()[:200], "payload": payload},
    )
    if not isinstance(result, list) or not result:
        raise CloudStorageError("The project was not confirmed as saved.")
    return result[0]


def list_projects(access_token):
    base, key = _settings()
    result = _request(
        "GET", f"{base}/rest/v1/sfw_projects",
        headers=_headers(key, access_token),
        params={"select": "id,title,payload,created_at,updated_at", "order": "updated_at.desc"},
    )
    if not isinstance(result, list):
        raise CloudStorageError("The project list response was invalid.")
    return result


def delete_project(access_token, project_id):
    base, key = _settings()
    _request(
        "DELETE", f"{base}/rest/v1/sfw_projects",
        headers=_headers(key, access_token, "return=minimal"),
        params={"id": f"eq.{project_id}"},
    )


def logout(access_token):
    base, key = _settings()
    _request(
        "POST", f"{base}/auth/v1/logout",
        headers=_headers(key, access_token),
    )
