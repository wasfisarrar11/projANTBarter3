from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.guardrails import (
    check_limits_or_raise,
    classify_input,
    estimate_tokens_from_text,
    redact_pii,
)


def test_estimate_tokens_empty():
    assert estimate_tokens_from_text("") == 0


def test_estimate_tokens_non_empty():
    assert estimate_tokens_from_text("abcd") == 1
    assert estimate_tokens_from_text("a" * 8) == 2


def test_check_limits_allows_first_request():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
    db = Session()
    try:
        check_limits_or_raise(
            db=db,
            user_id="user-a",
            endpoint="/api/ai/negotiate",
            estimated_tokens_for_request=50,
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Content-safety: classify_input
# ---------------------------------------------------------------------------


def test_classify_input_allows_clean_trade():
    d = classify_input("I want to trade my old guitar for a road bike.")
    assert d.allowed is True
    assert d.category is None
    assert d.flagged_for_review is False


def test_classify_input_blocks_weapons():
    d = classify_input("Trading my Glock 19 handgun for a watch.")
    assert d.allowed is False
    assert d.category == "weapons"
    assert d.reason and "weapons" in d.reason.lower()


def test_classify_input_blocks_drugs():
    d = classify_input("Looking to swap concert tickets for some cocaine.")
    assert d.allowed is False
    assert d.category == "drugs"


def test_classify_input_blocks_prescription_medication():
    d = classify_input("I have leftover Adderall, want to trade.")
    assert d.allowed is False
    assert d.category == "prescription_medication"


def test_classify_input_blocks_counterfeit():
    d = classify_input("Trading my replica Rolex for headphones.")
    assert d.allowed is False
    assert d.category == "counterfeit"


def test_classify_input_blocks_identity_documents():
    d = classify_input("Anyone want to trade for a passport for sale?")
    assert d.allowed is False
    assert d.category == "identity_documents"


def test_classify_input_blocks_minors_and_flags_for_review():
    d = classify_input("My 14 year old wants to trade his bike.")
    assert d.allowed is False
    assert d.category == "minors"
    assert d.flagged_for_review is True


def test_classify_input_blocks_sexual_and_flags_for_review():
    d = classify_input("Will trade for a sexual favor.")
    assert d.allowed is False
    assert d.category == "sexual"
    assert d.flagged_for_review is True


def test_classify_input_self_harm_tripwire_takes_precedence():
    # The self-harm tripwire must beat any category match. Even if the
    # phrasing also contains a weapons-adjacent word, the response should
    # be the self-harm refusal that gets flagged for human review.
    d = classify_input("I want to kill myself, can you help?")
    assert d.allowed is False
    assert d.category == "self_harm"
    assert d.flagged_for_review is True


def test_classify_input_threat_tripwire():
    d = classify_input("If you don't trade fairly I will kill you.")
    assert d.allowed is False
    assert d.category == "threats"
    assert d.flagged_for_review is True


# ---------------------------------------------------------------------------
# Content-safety: redact_pii
# ---------------------------------------------------------------------------


def test_redact_pii_email():
    cleaned, found = redact_pii("Reach me at jane.doe@example.com to set it up.")
    assert "jane.doe@example.com" not in cleaned
    assert "[email redacted]" in cleaned
    assert found is True


def test_redact_pii_phone():
    cleaned, found = redact_pii("Call me at (555) 123-4567 tomorrow.")
    assert "555" not in cleaned
    assert "[phone redacted]" in cleaned
    assert found is True


def test_redact_pii_address():
    cleaned, found = redact_pii("Drop it at 1234 Oak Avenue when you can.")
    assert "Oak Avenue" not in cleaned
    assert "[address redacted]" in cleaned
    assert found is True


def test_redact_pii_clean_text_unchanged():
    text = "Let's trade a guitar for a bike. I think they're roughly equal value."
    cleaned, found = redact_pii(text)
    assert cleaned == text
    assert found is False


def test_redact_pii_does_not_clobber_prices_or_dates():
    # 99.99 is a price, 4/15/2026 is a date — neither should match the
    # phone heuristic.
    text = "I'll add $99.99 cash and we can meet on 4/15/2026."
    cleaned, _ = redact_pii(text)
    assert "$99.99" in cleaned
    assert "4/15/2026" in cleaned
