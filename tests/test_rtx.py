import pytest

from sfw import rtx


def test_rtx_rejects_http_and_local_addresses():
    with pytest.raises(rtx.RTXError):
        rtx._validate_base_url("http://rtx.example.com")
    with pytest.raises(rtx.RTXError):
        rtx._validate_base_url("https://localhost:8090")
    with pytest.raises(rtx.RTXError):
        rtx._validate_base_url("https://127.0.0.1")


def test_rtx_rejects_private_dns_resolution(monkeypatch):
    monkeypatch.setattr(rtx.socket, "getaddrinfo", lambda *args, **kwargs: [
        (None, None, None, None, ("100.64.0.1", 443))
    ])
    with pytest.raises(rtx.RTXError):
        rtx._validate_base_url("https://rtx.example.com")


def test_rtx_accepts_public_dns_resolution(monkeypatch):
    monkeypatch.setattr(rtx.socket, "getaddrinfo", lambda *args, **kwargs: [
        (None, None, None, None, ("203.0.113.10", 443))
    ])
    # TEST-NET addresses are intentionally non-global, so use a public example address.
    monkeypatch.setattr(rtx.socket, "getaddrinfo", lambda *args, **kwargs: [
        (None, None, None, None, ("1.1.1.1", 443))
    ])
    assert rtx._validate_base_url("https://rtx.example.com") == "https://rtx.example.com"
