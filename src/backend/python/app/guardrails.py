from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .models import ApiUsage


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def estimate_tokens_from_text(text: str) -> int:
    # Cheap approximation: ~4 chars/token for English-ish text.
    # This is conservative enough for usage limits but not exact billing.
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

    # Requests in last 24h (rolling) and since month start.
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
