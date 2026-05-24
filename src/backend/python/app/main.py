import json

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .ai_negotiator import generate_agreement, negotiate
from .auth import get_current_user_id, reconcile_user_id
from .config import settings
from .database import Base, engine, get_db
from .models import AgreementDraft, NegotiationSession
from .guardrails import (
    SAFE_CANNED_RESPONSE,
    check_limits_or_raise,
    classify_input,
    classify_output,
    estimate_tokens_from_text,
    log_refusal,
    record_usage,
    redact_pii,
)
from .marketplace_library import fetch_marketplace_preview_context
from .schemas import AgreementRequest, AgreementResponse, NegotiateRequest, NegotiateResponse

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

_cors_origins = settings.cors_origins_list()
_cors_credentials = settings.CORS_ALLOW_CREDENTIALS
if "*" in _cors_origins:
    _cors_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": settings.APP_NAME}


def _persist_session(db, *, payload, effective_user_id, ai_response, moderation):
    """Persist a negotiation turn including the moderation decision.

    ``effective_user_id`` is the auth-resolved user_id, NOT whatever the
    client put in the body.
    """
    session = NegotiationSession(
        user_id=effective_user_id,
        listing_id=payload.listing_id,
        counterparty_listing_id=payload.counterparty_listing_id,
        messages_json=json.dumps(
            [m.model_dump() for m in payload.messages]
            + [{"role": "user", "content": payload.latest_user_message}]
            + [{"role": "assistant", "content": ai_response}]
            + [{"role": "moderation", "content": moderation}]
        ),
    )
    db.add(session)
    db.commit()


@app.post("/api/ai/negotiate", response_model=NegotiateResponse)
def ai_negotiate(
    payload: NegotiateRequest,
    db: Session = Depends(get_db),
    authenticated_user_id: str | None = Depends(get_current_user_id),
):
    # Auth: never trust payload.user_id in isolation. Authenticated id wins;
    # the body field is only honored when AUTH_REQUIRED=false.
    user_id = reconcile_user_id(authenticated_user_id, payload.user_id)

    if len(payload.latest_user_message) > settings.AI_MAX_INPUT_CHARS:
        raise HTTPException(status_code=413, detail="Message too long.")

    # Layer 1: input content-safety classifier.
    decision = classify_input(payload.latest_user_message)
    if not decision.allowed:
        moderation = {
            "blocked": True,
            "stage": "input",
            "category": decision.category,
            "flagged_for_review": decision.flagged_for_review,
        }
        _persist_session(
            db,
            payload=payload,
            effective_user_id=user_id,
            ai_response=decision.reason or "",
            moderation=moderation,
        )
        log_refusal(
            db=db,
            user_id=user_id,
            stage="input",
            category=decision.category,
            flagged_for_review=decision.flagged_for_review,
        )
        return NegotiateResponse(
            ai_response=decision.reason or "I can't help with that request.",
            status="refused",
            refusal_reason=decision.reason,
            refusal_category=decision.category,
            flagged_for_review=decision.flagged_for_review,
        )

    # Layer 2: rate / token budget check.
    estimated_tokens = (
        estimate_tokens_from_text(payload.latest_user_message)
        + settings.AI_MAX_OUTPUT_TOKENS
    )
    check_limits_or_raise(
        db=db,
        user_id=user_id,
        endpoint="/api/ai/negotiate",
        estimated_tokens_for_request=estimated_tokens,
    )

    mp_ctx = None
    if payload.marketplace_search_query:
        mp_ctx = fetch_marketplace_preview_context(
            q=payload.marketplace_search_query,
            listing_country_iso2=payload.marketplace_listing_country_iso2,
        )

    raw_response = negotiate(
        payload.messages,
        payload.latest_user_message,
        marketplace_context=mp_ctx,
    )

    # Layer 3: output classifier.
    output_decision = classify_output(raw_response)
    if not output_decision.allowed:
        moderation = {
            "blocked": True,
            "stage": "output",
            "category": output_decision.category,
            "flagged_for_review": output_decision.flagged_for_review,
        }
        _persist_session(
            db,
            payload=payload,
            effective_user_id=user_id,
            ai_response=SAFE_CANNED_RESPONSE,
            moderation=moderation,
        )
        log_refusal(
            db=db,
            user_id=user_id,
            stage="output",
            category=output_decision.category,
            flagged_for_review=output_decision.flagged_for_review,
        )
        record_usage(
            db=db,
            user_id=user_id,
            endpoint="/api/ai/negotiate",
            estimated_tokens=estimated_tokens,
        )
        return NegotiateResponse(
            ai_response=SAFE_CANNED_RESPONSE,
            status="refused",
            refusal_reason=output_decision.reason,
            refusal_category=output_decision.category,
            flagged_for_review=output_decision.flagged_for_review,
        )

    # Layer 4: PII redaction.
    ai_response, redacted = redact_pii(raw_response)

    moderation = {
        "blocked": False,
        "stage": "output",
        "redacted_pii": redacted,
    }
    _persist_session(
        db,
        payload=payload,
        effective_user_id=user_id,
        ai_response=ai_response,
        moderation=moderation,
    )

    record_usage(
        db=db,
        user_id=user_id,
        endpoint="/api/ai/negotiate",
        estimated_tokens=estimated_tokens,
    )

    return NegotiateResponse(ai_response=ai_response, status="ok")


@app.post("/api/agreements/generate", response_model=AgreementResponse)
def create_agreement(
    payload: AgreementRequest,
    db: Session = Depends(get_db),
    authenticated_user_id: str | None = Depends(get_current_user_id),
):
    user_id = reconcile_user_id(authenticated_user_id, payload.user_id)

    last_user_text = " ".join(
        m.content for m in payload.messages[-10:] if m.role == "user"
    )
    decision = classify_input(last_user_text)
    if not decision.allowed:
        log_refusal(
            db=db,
            user_id=user_id,
            stage="agreement_input",
            category=decision.category,
            flagged_for_review=decision.flagged_for_review,
        )
        return AgreementResponse(
            agreement_text=decision.reason or "I can't draft an agreement for that.",
            status="refused",
            refusal_reason=decision.reason,
            refusal_category=decision.category,
            flagged_for_review=decision.flagged_for_review,
        )

    estimated_tokens = settings.AI_MAX_OUTPUT_TOKENS + estimate_tokens_from_text(
        " ".join([m.content for m in payload.messages[-20:]])
    )
    check_limits_or_raise(
        db=db,
        user_id=user_id,
        endpoint="/api/agreements/generate",
        estimated_tokens_for_request=estimated_tokens,
    )

    jurisdiction = (
        (payload.jurisdiction or "").strip()
        or (settings.DEFAULT_AGREEMENT_JURISDICTION or "").strip()
        or "Not specified"
    )

    mp_ctx = None
    if payload.marketplace_search_query:
        mp_ctx = fetch_marketplace_preview_context(
            q=payload.marketplace_search_query,
            listing_country_iso2=payload.marketplace_listing_country_iso2,
        )

    raw_text = generate_agreement(
        payload.messages,
        jurisdiction,
        marketplace_context=mp_ctx,
    )

    output_decision = classify_output(raw_text)
    if not output_decision.allowed:
        log_refusal(
            db=db,
            user_id=user_id,
            stage="agreement_output",
            category=output_decision.category,
            flagged_for_review=output_decision.flagged_for_review,
        )
        record_usage(
            db=db,
            user_id=user_id,
            endpoint="/api/agreements/generate",
            estimated_tokens=estimated_tokens,
        )
        return AgreementResponse(
            agreement_text=SAFE_CANNED_RESPONSE,
            status="refused",
            refusal_reason=output_decision.reason,
            refusal_category=output_decision.category,
            flagged_for_review=output_decision.flagged_for_review,
        )

    agreement_text, _redacted = redact_pii(raw_text)

    draft = AgreementDraft(
        user_id=user_id,
        listing_id=payload.listing_id,
        counterparty_listing_id=payload.counterparty_listing_id,
        jurisdiction=jurisdiction,
        agreement_text=agreement_text,
    )
    db.add(draft)
    db.commit()

    record_usage(
        db=db,
        user_id=user_id,
        endpoint="/api/agreements/generate",
        estimated_tokens=estimated_tokens,
    )

    return AgreementResponse(agreement_text=agreement_text, status="ok")
