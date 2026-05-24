"""Safety + usage guardrails for the AI negotiator.

This module enforces THREE independent layers:

1. Quantity guardrails: per-user daily/monthly request counts and a monthly
   token budget. These protect the Anthropic API budget.

2. Input content guardrails: classification of user-supplied text against an
   explicit list of prohibited trade categories plus tripwires for self-harm
   and threats. Refusals short-circuit before any Anthropic call so they
   cost zero tokens.

3. Output content guardrails: classification of Claude's reply against the
   same prohibited list PLUS a separate "risky coordination" list (cash
   payments, wire transfers, meet-alone, address sharing, etc.). On a hit,
   the reply is replaced with a safe canned response instead of being shown
   to the user. PII is redacted regardless.

Plus: a structured refusal logger so emerging abuse patterns are visible in
the database without needing a separate observability stack.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .models import ApiUsage

log = logging.getLogger("antbarter.guardrails")


# ---------------------------------------------------------------------------
# Quantity guardrails
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def estimate_tokens_from_text(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def _month_start(dt: datetime) -> datetime:
    return datetime(dt.year, dt.month, 1, tzinfo=timezone.utc)


def check_limits_or_raise(
    *,
    db: Session,
    user_id: str,
    endpoint: str,
    estimated_tokens_for_request: int,
) -> None:
    now = _utc_now()
    day_start = now - timedelta(days=1)
    month_start = _month_start(now)

    daily_count = db.scalar(
        select(func.count(ApiUsage.id)).where(
            ApiUsage.user_id == user_id,
            ApiUsage.endpoint == endpoint,
            ApiUsage.created_at >= day_start,
        )
    )
    monthly_count = db.scalar(
        select(func.count(ApiUsage.id)).where(
            ApiUsage.user_id == user_id,
            ApiUsage.endpoint == endpoint,
            ApiUsage.created_at >= month_start,
        )
    )

    if daily_count is None:
        daily_count = 0
    if monthly_count is None:
        monthly_count = 0

    if daily_count >= settings.AI_MAX_REQUESTS_PER_DAY:
        raise HTTPException(
            status_code=429,
            detail="Daily AI limit reached. Try again tomorrow.",
        )
    if monthly_count >= settings.AI_MAX_REQUESTS_PER_MONTH:
        raise HTTPException(
            status_code=429,
            detail="Monthly AI limit reached. Try again next month.",
        )

    if settings.AI_MONTHLY_TOKEN_BUDGET > 0:
        monthly_tokens = db.scalar(
            select(func.coalesce(func.sum(ApiUsage.estimated_tokens), 0)).where(
                ApiUsage.user_id == user_id,
                ApiUsage.created_at >= month_start,
            )
        )
        monthly_tokens = int(monthly_tokens or 0)
        if monthly_tokens + estimated_tokens_for_request > settings.AI_MONTHLY_TOKEN_BUDGET:
            raise HTTPException(
                status_code=429,
                detail="Monthly AI token limit exceeded.",
            )


def record_usage(
    *,
    db: Session,
    user_id: str,
    endpoint: str,
    estimated_tokens: int,
) -> None:
    db.add(
        ApiUsage(
            user_id=user_id,
            endpoint=endpoint,
            estimated_tokens=int(max(0, estimated_tokens)),
        )
    )
    db.commit()


# ---------------------------------------------------------------------------
# Content guardrails
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    category: Optional[str] = None
    reason: Optional[str] = None
    flagged_for_review: bool = False


PROHIBITED_CATEGORIES = {
    "weapons": (
        "firearm", "firearms", "handgun", "rifle", "shotgun",
        "ammunition", "ammo round", "ghost gun", "silencer", "suppressor",
        "bump stock", "auto sear", "switchblade", "explosive", "bomb",
        "grenade", "ied", "tannerite", "glock",
    ),
    "drugs": (
        "cocaine", "heroin", "meth ", "methamphetamine", "fentanyl",
        "lsd", "mdma", "ecstasy pill", "ketamine", "psilocybin",
        "magic mushrooms", "crack rock", "weed for sale", "marijuana for sale",
    ),
    "prescription_medication": (
        "adderall", "xanax", "oxycodone", "oxycontin", "percocet",
        "vicodin", "hydrocodone", "tramadol", "ozempic for sale",
        "antibiotics for sale", "prescription pills",
    ),
    "counterfeit": (
        "counterfeit", "fake id", "replica rolex", "replica gucci",
        "knockoff designer", "fake passport", "forged",
    ),
    "identity_documents": (
        "passport for sale", "driver's license for sale", "social security card",
        "ssn for sale", "birth certificate for sale", "green card for sale",
    ),
    "live_animals": (
        "puppy for trade", "kitten for trade", "exotic pet", "live animal",
        "selling my dog", "selling my cat", "trading my pet",
    ),
    "minors": (
        "child for", "minor for trade", "underage", "13 year old",
        "14 year old", "15 year old", "16 year old", "17 year old",
    ),
    "sexual": (
        "sex for trade", "sexual favor", "escort service", "nude photos",
        "porn collection", "onlyfans account",
    ),
}

TRIPWIRE_PATTERNS = {
    "self_harm": (
        "kill myself", "end my life", "suicide", "want to die",
    ),
    "threats": (
        "kill you", "hurt you", "i will find you", "i'll find you",
        "burn your house",
    ),
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _extra_blocklist_terms():
    raw = (settings.SAFETY_EXTRA_BLOCKLIST or "").strip()
    if not raw:
        return []
    return [t.strip().lower() for t in raw.split(",") if t.strip()]


_REFUSAL_COPY = {
    "weapons":
        "I can't help negotiate trades involving weapons or ammunition.",
    "drugs":
        "I can't help negotiate trades involving controlled substances.",
    "prescription_medication":
        "I can't help negotiate trades involving prescription medication.",
    "counterfeit":
        "I can't help negotiate trades involving counterfeit goods.",
    "identity_documents":
        "I can't help negotiate trades involving identity documents.",
    "live_animals":
        "I can't help negotiate trades involving live animals on this platform.",
    "minors":
        "I can't help with anything involving a minor as a party or subject of a trade.",
    "sexual":
        "I can't help with sexual content or services.",
    "extra":
        "This request is outside what I'm allowed to help with on AntBarter.",
    "self_harm":
        "It sounds like you might be going through something serious. "
        "I'm not able to continue this trade conversation, and I've flagged "
        "the thread for human review. If you're in crisis, please contact "
        "your local emergency services or a crisis line.",
    "threats":
        "I've flagged this conversation for human review and can't continue.",
}


def classify_input(text: str) -> SafetyDecision:
    if not settings.SAFETY_MODERATION_ENABLED:
        return SafetyDecision(allowed=True)

    norm = _normalize(text)
    if not norm:
        return SafetyDecision(allowed=True)

    for category, triggers in TRIPWIRE_PATTERNS.items():
        for t in triggers:
            if t in norm:
                return SafetyDecision(
                    allowed=False,
                    category=category,
                    reason=_REFUSAL_COPY[category],
                    flagged_for_review=True,
                )

    for category, triggers in PROHIBITED_CATEGORIES.items():
        for t in triggers:
            if t in norm:
                return SafetyDecision(
                    allowed=False,
                    category=category,
                    reason=_REFUSAL_COPY[category],
                    flagged_for_review=category in ("minors", "sexual"),
                )

    for term in _extra_blocklist_terms():
        if term and term in norm:
            return SafetyDecision(
                allowed=False,
                category="extra",
                reason=_REFUSAL_COPY["extra"],
                flagged_for_review=False,
            )

    return SafetyDecision(allowed=True)


# ---------------------------------------------------------------------------
# PII redaction
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

_PHONE_RE = re.compile(
    r"""
    (?<!\d)
    (?:\+?\d{1,3}[\s\-.])?
    (?:\(\d{2,4}\)[\s\-.]?|\d{2,4}[\s\-.])
    \d{2,4}[\s\-.]?\d{2,4}
    (?!\d)
    """,
    re.VERBOSE,
)

_ADDRESS_RE = re.compile(
    r"""
    \b
    \d{1,6}\s+
    (?:[A-Z][A-Za-z'.-]*\s+){1,5}
    (?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|
       Way|Court|Ct|Place|Pl|Terrace|Parkway|Pkwy|Highway|Hwy|Circle|Cir)
    \b\.?
    """,
    re.VERBOSE,
)


def redact_pii(text: str):
    if not text:
        return text, False

    found = False

    def _sub(pattern, placeholder, s):
        nonlocal found
        if pattern.search(s):
            found = True
            return pattern.sub(placeholder, s)
        return s

    out = _sub(_EMAIL_RE, "[email redacted]", text)
    out = _sub(_PHONE_RE, "[phone redacted]", out)
    out = _sub(_ADDRESS_RE, "[address redacted]", out)
    return out, found


# ---------------------------------------------------------------------------
# Output classifier: scans Claude's reply BEFORE it reaches the user.
# ---------------------------------------------------------------------------


RISKY_COORDINATION_PATTERNS = (
    "send cash",
    "send the cash",
    "mail cash",
    "mail the cash",
    "wire transfer",
    "wire the money",
    "western union",
    "moneygram",
    "zelle",
    "venmo me",
    "cash app",
    "cashapp",
    "gift card",
    "gift cards",
    "bitcoin",
    "crypto wallet",
    "cryptocurrency",
    "meet alone",
    "meet me alone",
    "come to my house",
    "come to my home",
    "my home address",
    "give your address",
    "send your address",
    "share your address",
    "give me your address",
    "give me your phone",
    "give me your number",
    "send your phone",
    "share your phone number",
    "send your social",
    "social security number",
    "ssn",
    "bank account number",
    "routing number",
)


SAFE_CANNED_RESPONSE = (
    "AntBarter Assistant (AI):\n"
    "The previous draft response was held back by the safety filter. "
    "For your protection, please coordinate trades through AntBarter's "
    "in-platform messaging, agree to meet only in a public location, and "
    "do not share your home address, phone number, or financial account "
    "details in chat. If you believe this listing is unsafe, report it "
    "from the listing page so a human reviewer can take a look."
)


def classify_output(text: str) -> SafetyDecision:
    """Run Claude's reply through the prohibited-category list plus the
    risky-coordination list."""
    if not settings.SAFETY_MODERATION_ENABLED:
        return SafetyDecision(allowed=True)

    norm = _normalize(text)
    if not norm:
        return SafetyDecision(allowed=True)

    for category, triggers in PROHIBITED_CATEGORIES.items():
        for t in triggers:
            if t in norm:
                return SafetyDecision(
                    allowed=False,
                    category=category,
                    reason=_REFUSAL_COPY[category],
                    flagged_for_review=category in ("minors", "sexual"),
                )

    for t in RISKY_COORDINATION_PATTERNS:
        if t in norm:
            return SafetyDecision(
                allowed=False,
                category="risky_coordination",
                reason=(
                    "The assistant suggested an unsafe coordination pattern; "
                    "the message has been replaced with a safer template."
                ),
                flagged_for_review=False,
            )

    return SafetyDecision(allowed=True)


# ---------------------------------------------------------------------------
# Structured refusal logging
# ---------------------------------------------------------------------------


def log_refusal(
    *,
    db: Session,
    user_id: str,
    stage: str,
    category: Optional[str],
    flagged_for_review: bool,
) -> None:
    """Persist a structured refusal record + emit an application log line."""
    safe_category = (category or "unknown")[:80]
    safe_stage = (stage or "input")[:80]
    log.warning(
        "antbarter_refusal user=%s stage=%s category=%s flagged_for_review=%s",
        user_id,
        safe_stage,
        safe_category,
        flagged_for_review,
    )
    try:
        db.add(
            ApiUsage(
                user_id=user_id,
                endpoint=f"safety/refusal:{safe_stage}:{safe_category}",
                estimated_tokens=0,
            )
        )
        db.commit()
    except Exception:  # pragma: no cover - logging must never raise
        log.exception("Failed to persist refusal record for user=%s", user_id)
        try:
            db.rollback()
        except Exception:
            pass
