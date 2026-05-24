"""Tests for the output content classifier in app.guardrails."""
from app.guardrails import (
    RISKY_COORDINATION_PATTERNS,
    SAFE_CANNED_RESPONSE,
    classify_output,
)


def test_classify_output_allows_clean_negotiation_reply():
    text = (
        "AntBarter Assistant (AI):\n"
        "Both items appear roughly comparable. Consider proposing a public "
        "weekend meet-up and confirming condition before exchange."
    )
    d = classify_output(text)
    assert d.allowed is True
    assert d.category is None


def test_classify_output_blocks_prohibited_category_in_reply():
    """Even if the model somehow produced text in a banned category (jailbreak,
    prompt injection from the marketplace context block), the output layer
    must catch it and refuse before showing the user.
    """
    text = (
        "AntBarter Assistant (AI):\n"
        "You could trade your bike for a Glock 19 handgun at a fair price."
    )
    d = classify_output(text)
    assert d.allowed is False
    assert d.category == "weapons"


def test_classify_output_blocks_wire_transfer_suggestion():
    text = (
        "AntBarter Assistant (AI):\n"
        "Have the buyer send a wire transfer for the difference and you "
        "ship the laptop afterward."
    )
    d = classify_output(text)
    assert d.allowed is False
    assert d.category == "risky_coordination"


def test_classify_output_blocks_address_request():
    text = (
        "AntBarter Assistant (AI):\n"
        "Ask them to share your address so they can ship the item directly."
    )
    d = classify_output(text)
    assert d.allowed is False
    assert d.category == "risky_coordination"


def test_classify_output_blocks_meet_alone():
    text = (
        "AntBarter Assistant (AI):\n"
        "If you'd like, you can meet alone at a quiet spot to do the swap."
    )
    d = classify_output(text)
    assert d.allowed is False
    assert d.category == "risky_coordination"


def test_classify_output_blocks_gift_card_payment():
    text = (
        "AntBarter Assistant (AI):\n"
        "Settle the value gap with a gift card sent over email."
    )
    d = classify_output(text)
    assert d.allowed is False
    assert d.category == "risky_coordination"


def test_safe_canned_response_starts_with_required_prefix():
    """The replacement message itself must obey the prefix requirement so the
    user always sees a consistent AI label, including on refusals."""
    assert SAFE_CANNED_RESPONSE.startswith("AntBarter Assistant (AI):")


def test_risky_coordination_patterns_are_lowercase_and_nonempty():
    """Sanity check on the constant -- prevents the all-too-easy regression
    where someone adds a casing-mixed phrase that classify_output (which
    lowercases the input) will never match."""
    assert len(RISKY_COORDINATION_PATTERNS) >= 10
    for p in RISKY_COORDINATION_PATTERNS:
        assert p == p.lower()
        assert p.strip()
