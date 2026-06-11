"""Stripe billing helpers.

Security ground rules (do not relax without security review):

1.  ``STRIPE_SECRET_KEY`` is loaded from environment ONLY. It must never be
    sent to the browser or written to source control. Frontend code calls
    /api/subscribe which returns a one-time Checkout URL; the secret stays
    server-side.

2.  The price the user is charged is determined by ``STRIPE_PRICE_ID`` on the
    server. The frontend cannot pass a price, plan id, or amount. This
    prevents a malicious client from creating a $0 checkout against our
    account.

3.  Subscription status is mirrored to the local DB by webhook events whose
    signature is verified with ``STRIPE_WEBHOOK_SECRET``. Unsigned or
    badly-signed webhook posts are rejected with 400. Without a webhook
    secret configured, the webhook endpoint refuses every request.

4.  The effective ``user_id`` is the authenticated one from the bearer token,
    not anything the client puts in the body. See ``auth.reconcile_user_id``.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .config import settings
from .models import Subscription

log = logging.getLogger("antbarter.billing")

try:
    import stripe  # type: ignore
except Exception:  # pragma: no cover - dependency optional during dev
    stripe = None


def _configure_stripe():
    if stripe is None:
        return None
    if not settings.STRIPE_SECRET_KEY:
        return None
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def get_or_create_subscription_row(db: Session, user_id: str) -> Subscription:
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if sub:
        return sub
    sub = Subscription(user_id=user_id, status="pending")
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def is_subscribed(db: Session, user_id: str) -> bool:
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if not sub:
        return False
    return sub.status in ("active", "trialing")


def create_checkout_session(
    *,
    db: Session,
    user_id: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create a Stripe Checkout Session and return its URL.

    Raises ``RuntimeError`` if Stripe is not configured. The price is taken
    from server config, never from the request body.
    """
    s = _configure_stripe()
    if s is None:
        raise RuntimeError("Stripe is not configured on this server.")
    if not settings.STRIPE_PRICE_ID:
        raise RuntimeError("STRIPE_PRICE_ID is not configured.")

    sub_row = get_or_create_subscription_row(db, user_id)

    session_kwargs = {
        "mode": "subscription",
        "line_items": [{"price": settings.STRIPE_PRICE_ID, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        # client_reference_id is echoed back on the webhook so we can match
        # the Checkout completion to our internal user.
        "client_reference_id": user_id,
        "metadata": {"user_id": user_id},
    }
    if sub_row.stripe_customer_id:
        session_kwargs["customer"] = sub_row.stripe_customer_id

    checkout = s.checkout.Session.create(**session_kwargs)
    if not checkout.url:
        raise RuntimeError("Stripe did not return a checkout URL.")
    return checkout.url


def verify_webhook(payload: bytes, signature_header: Optional[str]):
    """Return the verified event dict or raise ValueError."""
    s = _configure_stripe()
    if s is None:
        raise ValueError("Stripe is not configured.")
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise ValueError("Webhook secret not configured; refusing event.")
    if not signature_header:
        raise ValueError("Missing Stripe-Signature header.")
    return s.Webhook.construct_event(
        payload, signature_header, settings.STRIPE_WEBHOOK_SECRET
    )


def _update_status(
    db: Session,
    *,
    user_id: str,
    status: str,
    customer_id: str = "",
    subscription_id: str = "",
) -> None:
    sub = get_or_create_subscription_row(db, user_id)
    sub.status = status
    if customer_id:
        sub.stripe_customer_id = customer_id
    if subscription_id:
        sub.stripe_subscription_id = subscription_id
    sub.updated_at = datetime.utcnow()
    db.add(sub)
    db.commit()


def apply_webhook_event(db: Session, event: dict) -> None:
    """Translate a Stripe webhook event into a local status update.

    Handled events:
      * checkout.session.completed       -> status="active"
      * customer.subscription.updated    -> mirror Stripe's status string
      * customer.subscription.deleted    -> status="canceled"
    All other events are accepted (200) and ignored.
    """
    etype = event.get("type") or ""
    data = (event.get("data") or {}).get("object") or {}

    if etype == "checkout.session.completed":
        user_id = data.get("client_reference_id") or (data.get("metadata") or {}).get(
            "user_id"
        )
        if not user_id:
            log.warning("checkout.session.completed without user_id metadata")
            return
        _update_status(
            db,
            user_id=user_id,
            status="active",
            customer_id=data.get("customer") or "",
            subscription_id=data.get("subscription") or "",
        )
        return

    if etype in ("customer.subscription.updated", "customer.subscription.created"):
        sub_id = data.get("id") or ""
        status = data.get("status") or "active"
        sub = (
            db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == sub_id)
            .first()
            if sub_id
            else None
        )
        if not sub:
            log.warning("subscription event for unknown subscription_id=%s", sub_id)
            return
        sub.status = status
        sub.updated_at = datetime.utcnow()
        db.add(sub)
        db.commit()
        return

    if etype == "customer.subscription.deleted":
        sub_id = data.get("id") or ""
        sub = (
            db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == sub_id)
            .first()
            if sub_id
            else None
        )
        if not sub:
            return
        sub.status = "canceled"
        sub.updated_at = datetime.utcnow()
        db.add(sub)
        db.commit()
        return
