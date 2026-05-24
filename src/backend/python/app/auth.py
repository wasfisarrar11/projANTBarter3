"""Authentication dependency for the AntBarter AI backend.

This is a deliberately small, dependency-free auth shim. Its purpose is to
stop the AI endpoints from trusting whatever ``user_id`` the client puts in
the request body. Until this lands, any caller could spoof another user's
quota, refusal log, and negotiation history simply by changing one field.

Three accepted token shapes (in priority order):

1. ``dev:<user_id>`` — a development-only opaque token. Allowed when
   ``settings.AUTH_DEV_TOKENS_ALLOWED`` is True. NEVER enable this in
   production: it is a "trust the bearer" token with no signature.

2. HS256 JWT signed with ``settings.AUTH_JWT_SECRET``. The ``sub`` claim is
   used as the user_id. ``iss`` and ``aud`` are validated against the
   configured issuer/audience. ``exp`` is enforced if present.

3. (Future) Cognito-issued JWT verified against the JWKS at
   ``deployment/cognito-setup.md``. Swap ``_verify_jwt`` for a JWKS-based
   implementation when you cut over.

Behavior is controlled by ``settings.AUTH_REQUIRED``:

* ``AUTH_REQUIRED=true``: every protected endpoint requires a valid token.
  Missing/invalid tokens return ``401``.

* ``AUTH_REQUIRED=false`` (default): if a token is present and valid, the
  authenticated user_id wins; if absent, the endpoint falls back to the
  client-supplied user_id with a warning logged. This preserves backward
  compatibility for existing tests and local dev while still letting you
  start sending tokens from the frontend.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Optional

from fastapi import Header, HTTPException, status

from .config import settings

log = logging.getLogger("antbarter.auth")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _verify_jwt(token: str) -> Optional[str]:
    """Verify an HS256 JWT and return the ``sub`` claim, or None on failure.

    No third-party dependency: this is intentionally a tiny verifier. For
    production rotation/KMS/JWKS, replace this function rather than the
    callers.
    """
    secret = settings.AUTH_JWT_SECRET
    if not secret:
        return None

    parts = token.split(".")
    if len(parts) != 3:
        return None

    try:
        header = json.loads(_b64url_decode(parts[0]))
        payload = json.loads(_b64url_decode(parts[1]))
        signature = _b64url_decode(parts[2])
    except Exception:
        return None

    if header.get("alg") != "HS256" or header.get("typ") not in (None, "JWT"):
        return None

    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    expected = hmac.new(
        secret.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    if not hmac.compare_digest(expected, signature):
        return None

    # Validate standard claims.
    iss = payload.get("iss")
    if settings.AUTH_JWT_ISSUER and iss != settings.AUTH_JWT_ISSUER:
        return None
    aud = payload.get("aud")
    if settings.AUTH_JWT_AUDIENCE and aud != settings.AUTH_JWT_AUDIENCE:
        return None
    exp = payload.get("exp")
    if exp is not None:
        try:
            if int(exp) < int(time.time()):
                return None
        except (TypeError, ValueError):
            return None

    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        return None
    return sub.strip()


def _parse_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def resolve_authenticated_user_id(
    authorization: Optional[str] = Header(default=None),
) -> Optional[str]:
    """Pure resolver: return the user_id from the Authorization header, or
    None if no valid token is present. Does NOT raise; that lets callers
    decide based on AUTH_REQUIRED whether absence is fatal."""
    token = _parse_bearer(authorization)
    if not token:
        return None

    # Dev token shape: "dev:<user_id>"
    if settings.AUTH_DEV_TOKENS_ALLOWED and token.startswith("dev:"):
        candidate = token[4:].strip()
        if candidate:
            return candidate

    return _verify_jwt(token)


def get_current_user_id(
    authorization: Optional[str] = Header(default=None),
) -> Optional[str]:
    """FastAPI dependency. Returns the authenticated user_id or None.

    When ``AUTH_REQUIRED`` is True, missing/invalid tokens raise 401.
    When False, returns None and the endpoint falls back to the request body.
    """
    user_id = resolve_authenticated_user_id(authorization)
    if user_id:
        return user_id

    if settings.AUTH_REQUIRED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return None


def reconcile_user_id(authenticated: Optional[str], claimed: str) -> str:
    """Choose the effective user_id and log when the client lied.

    * If we have an authenticated user_id, it ALWAYS wins. If the body's
      user_id differs, that's a tampering signal worth logging.
    * If we don't (AUTH_REQUIRED=false and no token), fall back to the
      claimed user_id with a deprecation warning.
    """
    if authenticated:
        if claimed and claimed != authenticated:
            log.warning(
                "antbarter_auth_mismatch authenticated=%s claimed=%s — "
                "using authenticated user_id",
                authenticated,
                claimed,
            )
        return authenticated

    log.warning(
        "antbarter_auth_unauthenticated claimed=%s — set AUTH_REQUIRED=true "
        "to reject these requests",
        claimed,
    )
    return claimed
