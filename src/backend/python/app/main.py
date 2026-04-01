import json

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .ai_negotiator import generate_agreement, negotiate
from .config import settings
from .database import Base, engine, get_db
from .models import AgreementDraft, NegotiationSession
from .guardrails import check_limits_or_raise, estimate_tokens_from_text, record_usage
from .schemas import AgreementRequest, AgreementResponse, NegotiateRequest, NegotiateResponse

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": settings.APP_NAME}


@app.post("/api/ai/negotiate", response_model=NegotiateResponse)
def ai_negotiate(payload: NegotiateRequest, db: Session = Depends(get_db)):
    if len(payload.latest_user_message) > settings.AI_MAX_INPUT_CHARS:
        raise HTTPException(status_code=413, detail="Message too long.")

    estimated_tokens = (
        estimate_tokens_from_text(payload.latest_user_message)
        + settings.AI_MAX_OUTPUT_TOKENS
    )
    check_limits_or_raise(
        db=db,
        user_id=payload.user_id,
        endpoint="/api/ai/negotiate",
        estimated_tokens_for_request=estimated_tokens,
    )

    ai_response = negotiate(payload.messages, payload.latest_user_message)

    session = NegotiationSession(
        user_id=payload.user_id,
        listing_id=payload.listing_id,
        counterparty_listing_id=payload.counterparty_listing_id,
        messages_json=json.dumps(
            [m.model_dump() for m in payload.messages]
            + [{"role": "user", "content": payload.latest_user_message}]
            + [{"role": "assistant", "content": ai_response}]
        ),
    )
    db.add(session)
    db.commit()

    record_usage(
        db=db,
        user_id=payload.user_id,
        endpoint="/api/ai/negotiate",
        estimated_tokens=estimated_tokens,
    )

    return NegotiateResponse(ai_response=ai_response)


@app.post("/api/agreements/generate", response_model=AgreementResponse)
def create_agreement(payload: AgreementRequest, db: Session = Depends(get_db)):
    # Agreements tend to be longer; keep hard cap but rely on output cap too.
    estimated_tokens = settings.AI_MAX_OUTPUT_TOKENS + estimate_tokens_from_text(
        " ".join([m.content for m in payload.messages[-20:]])
    )
    check_limits_or_raise(
        db=db,
        user_id=payload.user_id,
        endpoint="/api/agreements/generate",
        estimated_tokens_for_request=estimated_tokens,
    )

    agreement_text = generate_agreement(payload.messages, payload.jurisdiction)

    draft = AgreementDraft(
        user_id=payload.user_id,
        listing_id=payload.listing_id,
        counterparty_listing_id=payload.counterparty_listing_id,
        jurisdiction=payload.jurisdiction,
        agreement_text=agreement_text,
    )
    db.add(draft)
    db.commit()

    record_usage(
        db=db,
        user_id=payload.user_id,
        endpoint="/api/agreements/generate",
        estimated_tokens=estimated_tokens,
    )

    return AgreementResponse(agreement_text=agreement_text)
