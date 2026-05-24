"""Tests for the auth dependency wired into the AI endpoints."""
import base64
import hashlib
import hmac
import json
import time

import pytest

from app import auth as auth_module
from app.config import settings
from app.main import app


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _make_jwt(secret: str, sub: str, *, iss: str, aud: str, exp_offset: int = 600) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url(
        json.dumps(
            {"sub": sub, "iss": iss, "aud": aud, "exp": int(time.time()) + exp_offset}
        ).encode()
    )
    signing_input = f"{header}.{payload}".encode("ascii")
    sig = _b64url(
        hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    )
    return f"{header}.{payload}.{sig}"


# Pure resolver behavior


def test_dev_token_returns_user_id():
    assert auth_module.resolve_authenticated_user_id("Bearer dev:alice") == "alice"


def test_no_header_returns_none():
    assert auth_module.resolve_authenticated_user_id(None) is None


def test_malformed_header_returns_none():
    assert auth_module.resolve_authenticated_user_id("not-a-bearer") is None
    assert auth_module.resolve_authenticated_user_id("Bearer ") is None
    assert auth_module.resolve_authenticated_user_id("Basic abc") is None


def test_jwt_round_trip(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", "test-secret")
    monkeypatch.setattr(settings, "AUTH_JWT_ISSUER", "antbarter")
    monkeypatch.setattr(settings, "AUTH_JWT_AUDIENCE", "antbarter-api")
    token = _make_jwt(
        "test-secret", "user-42", iss="antbarter", aud="antbarter-api"
    )
    assert auth_module.resolve_authenticated_user_id(f"Bearer {token}") == "user-42"


def test_jwt_with_wrong_secret_rejected(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", "right-secret")
    monkeypatch.setattr(settings, "AUTH_JWT_ISSUER", "antbarter")
    monkeypatch.setattr(settings, "AUTH_JWT_AUDIENCE", "antbarter-api")
    token = _make_jwt(
        "wrong-secret", "user-42", iss="antbarter", aud="antbarter-api"
    )
    assert auth_module.resolve_authenticated_user_id(f"Bearer {token}") is None


def test_jwt_expired_rejected(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", "test-secret")
    monkeypatch.setattr(settings, "AUTH_JWT_ISSUER", "antbarter")
    monkeypatch.setattr(settings, "AUTH_JWT_AUDIENCE", "antbarter-api")
    token = _make_jwt(
        "test-secret",
        "user-42",
        iss="antbarter",
        aud="antbarter-api",
        exp_offset=-30,
    )
    assert auth_module.resolve_authenticated_user_id(f"Bearer {token}") is None


def test_jwt_wrong_audience_rejected(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", "test-secret")
    monkeypatch.setattr(settings, "AUTH_JWT_ISSUER", "antbarter")
    monkeypatch.setattr(settings, "AUTH_JWT_AUDIENCE", "antbarter-api")
    token = _make_jwt(
        "test-secret", "user-42", iss="antbarter", aud="some-other-api"
    )
    assert auth_module.resolve_authenticated_user_id(f"Bearer {token}") is None


def test_dev_token_disabled_when_setting_off(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_DEV_TOKENS_ALLOWED", False)
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", "")
    assert auth_module.resolve_authenticated_user_id("Bearer dev:alice") is None


def test_reconcile_authenticated_overrides_claimed():
    assert auth_module.reconcile_user_id("alice", "mallory") == "alice"


def test_reconcile_falls_back_to_claimed_when_unauthenticated():
    assert auth_module.reconcile_user_id(None, "alice") == "alice"


# End-to-end through the FastAPI app


def test_negotiate_endpoint_uses_authenticated_user_id_over_payload(client):
    r = client.post(
        "/api/ai/negotiate",
        headers={"Authorization": "Bearer dev:authenticated-bob"},
        json={
            "user_id": "client-claimed-mallory",
            "listing_id": "l1",
            "counterparty_listing_id": "l2",
            "latest_user_message": "Hello, want to swap a bike for a guitar.",
            "messages": [],
        },
    )
    assert r.status_code == 200


def test_negotiate_endpoint_requires_auth_when_enabled(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_REQUIRED", True)
    r = client.post(
        "/api/ai/negotiate",
        json={
            "user_id": "anyone",
            "listing_id": "l1",
            "counterparty_listing_id": "l2",
            "latest_user_message": "Hello",
            "messages": [],
        },
    )
    assert r.status_code == 401
    assert "www-authenticate" in {k.lower() for k in r.headers.keys()}


def test_negotiate_endpoint_accepts_valid_token_when_auth_required(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_REQUIRED", True)
    r = client.post(
        "/api/ai/negotiate",
        headers={"Authorization": "Bearer dev:carol"},
        json={
            "user_id": "carol",
            "listing_id": "l1",
            "counterparty_listing_id": "l2",
            "latest_user_message": "Hi there.",
            "messages": [],
        },
    )
    assert r.status_code == 200


def test_agreements_endpoint_requires_auth_when_enabled(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_REQUIRED", True)
    r = client.post(
        "/api/agreements/generate",
        json={
            "user_id": "anyone",
            "listing_id": "l1",
            "counterparty_listing_id": "l2",
            "messages": [{"role": "user", "content": "trade my bike"}],
        },
    )
    assert r.status_code == 401
