import pytest

from sfw import cloud_storage


class FakeResponse:
    def __init__(self, status=200, data=None):
        self.status_code = status
        self._data = data
        self.content = b"" if data is None else b"{}"

    def json(self):
        return self._data


def test_supabase_config_requires_https(monkeypatch):
    # Patch the setting source so the real URL validation is exercised.
    from sfw import config
    monkeypatch.setattr(config, "_setting", lambda name: {
        "SFW_SUPABASE_URL": "http://example.com",
        "SFW_SUPABASE_ANON_KEY": "anon",
    }.get(name, ""))
    with pytest.raises(cloud_storage.CloudStorageError, match="HTTPS"):
        cloud_storage._settings()


def test_sign_in_uses_password_grant_and_anon_key(monkeypatch):
    from sfw import config
    monkeypatch.setattr(config, "_setting", lambda name: {
        "SFW_SUPABASE_URL": "https://project.supabase.co",
        "SFW_SUPABASE_ANON_KEY": "public-anon",
    }.get(name, ""))
    seen = {}

    def fake_request(method, url, **kwargs):
        seen.update(method=method, url=url, **kwargs)
        return FakeResponse(data={"access_token": "user-token", "refresh_token": "refresh"})

    monkeypatch.setattr(cloud_storage.requests, "request", fake_request)
    result = cloud_storage.sign_in(" user@example.com ", "password")
    assert result["access_token"] == "user-token"
    assert seen["url"].endswith("/auth/v1/token?grant_type=password")
    assert seen["headers"]["apikey"] == "public-anon"
    assert seen["json"]["email"] == "user@example.com"


def test_project_save_uses_user_token_and_never_service_role(monkeypatch):
    from sfw import config
    monkeypatch.setattr(config, "_setting", lambda name: {
        "SFW_SUPABASE_URL": "https://project.supabase.co",
        "SFW_SUPABASE_ANON_KEY": "public-anon",
    }.get(name, ""))
    seen = {}

    def fake_request(method, url, **kwargs):
        seen.update(method=method, url=url, **kwargs)
        return FakeResponse(data=[{"id": "project-id", "title": "Maize"}])

    monkeypatch.setattr(cloud_storage.requests, "request", fake_request)
    result = cloud_storage.save_project("user-token", "Maize", {"aim": "test"})
    assert result["id"] == "project-id"
    assert seen["headers"]["Authorization"] == "Bearer user-token"
    assert seen["headers"]["apikey"] == "public-anon"
    assert seen["json"]["payload"]["aim"] == "test"


def test_unauthorized_response_requests_reauthentication(monkeypatch):
    from sfw import config
    monkeypatch.setattr(config, "_setting", lambda name: {
        "SFW_SUPABASE_URL": "https://project.supabase.co",
        "SFW_SUPABASE_ANON_KEY": "public-anon",
    }.get(name, ""))

    def fake_request(*args, **kwargs):
        return FakeResponse(status=401, data={"message": "expired"})

    monkeypatch.setattr(cloud_storage.requests, "request", fake_request)
    with pytest.raises(cloud_storage.CloudStorageError, match="Sign in again"):
        cloud_storage.list_projects("expired-token")
