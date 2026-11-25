import pytest

from sfw import cloud_storage


class FakeResponse:
    def __init__(self, data, status=200):
        self.status_code = status
        self._data = data
        self.content = b"{}"

    def json(self):
        return self._data


def configure_supabase(monkeypatch):
    from sfw import config
    monkeypatch.setattr(config, "_setting", lambda name: {
        "SFW_SUPABASE_URL": "https://project.supabase.co",
        "SFW_SUPABASE_ANON_KEY": "public-anon",
    }.get(name, ""))


def test_list_public_subscription_plans_uses_anon_key(monkeypatch):
    configure_supabase(monkeypatch)
    seen = {}

    def fake_request(method, url, **kwargs):
        seen.update(method=method, url=url, **kwargs)
        return FakeResponse([{"code": "student", "amount_kes": 299}])

    monkeypatch.setattr(cloud_storage.requests, "request", fake_request)
    result = cloud_storage.list_subscription_plans()

    assert result[0]["amount_kes"] == 299
    assert seen["url"].endswith("/rest/v1/sfw_plans")
    assert seen["headers"]["apikey"] == "public-anon"
    assert "Authorization" not in seen["headers"]


def test_my_subscription_history_uses_user_token_and_bounded_limit(monkeypatch):
    configure_supabase(monkeypatch)
    seen = {}

    def fake_request(method, url, **kwargs):
        seen.update(method=method, url=url, **kwargs)
        return FakeResponse([])

    monkeypatch.setattr(cloud_storage.requests, "request", fake_request)
    assert cloud_storage.list_my_subscriptions("user-token", limit=500) == []
    assert seen["headers"]["Authorization"] == "Bearer user-token"
    assert seen["params"]["limit"] == 100


def test_mpesa_initiation_sends_plan_and_phone_not_client_price(monkeypatch):
    configure_supabase(monkeypatch)
    seen = {}

    def fake_request(method, url, **kwargs):
        seen.update(method=method, url=url, **kwargs)
        return FakeResponse({"ok": True, "checkout_request_id": "ws_CO_123"})

    monkeypatch.setattr(cloud_storage.requests, "request", fake_request)
    result = cloud_storage.start_mpesa_payment("user-token", "student", "0712345678")

    assert result["ok"] is True
    assert seen["url"].endswith("/functions/v1/mpesa-stk-push")
    assert seen["headers"]["Authorization"] == "Bearer user-token"
    assert seen["json"] == {"plan_code": "student", "phone_number": "0712345678"}
    assert "amount_kes" not in seen["json"]


def test_mpesa_initiation_rejects_missing_plan(monkeypatch):
    configure_supabase(monkeypatch)
    with pytest.raises(cloud_storage.CloudStorageError, match="Choose a subscription plan"):
        cloud_storage.start_mpesa_payment("user-token", "", "0712345678")


def test_admin_subscription_listing_requires_admin(monkeypatch):
    monkeypatch.setattr(cloud_storage, "is_admin", lambda token: False)
    with pytest.raises(cloud_storage.CloudStorageError, match="Administrator access"):
        cloud_storage.list_all_subscriptions("ordinary-user-token")


def test_admin_payment_listing_requires_admin(monkeypatch):
    monkeypatch.setattr(cloud_storage, "is_admin", lambda token: False)
    with pytest.raises(cloud_storage.CloudStorageError, match="Administrator access"):
        cloud_storage.list_all_payments("ordinary-user-token")
