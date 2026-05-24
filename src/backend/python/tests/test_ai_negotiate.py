def test_ai_negotiate_without_api_key_returns_placeholder(client):
    r = client.post(
        "/api/ai/negotiate",
        json={
            "user_id": "u1",
            "listing_id": "l1",
            "counterparty_listing_id": "l2",
            "latest_user_message": "Hello",
            "messages": [],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "ai_response" in data
    assert data["status"] == "ok"
    assert "ANTHROPIC_API_KEY" in data["ai_response"] or "not configured" in data["ai_response"]


def test_ai_negotiate_refuses_prohibited_category_without_calling_claude(client):
    """Prohibited input must be refused at the API boundary.

    The test environment has no ANTHROPIC_API_KEY; the existing placeholder
    test proves that a normal request would otherwise hit the "not
    configured" fallback. If we get back a refusal here instead, that's
    proof the input classifier short-circuited before the negotiator was
    even consulted.
    """
    r = client.post(
        "/api/ai/negotiate",
        json={
            "user_id": "u1",
            "listing_id": "l1",
            "counterparty_listing_id": "l2",
            "latest_user_message": "I want to trade my Glock 19 handgun for a laptop.",
            "messages": [],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "refused"
    assert data["refusal_category"] == "weapons"
    # The refusal message must not be the "API key not configured" string —
    # if it were, the classifier hadn't fired and we'd be paying for tokens.
    assert "ANTHROPIC_API_KEY" not in data["ai_response"]


def test_ai_negotiate_self_harm_is_flagged_for_review(client):
    r = client.post(
        "/api/ai/negotiate",
        json={
            "user_id": "u1",
            "listing_id": "l1",
            "counterparty_listing_id": "l2",
            "latest_user_message": "I want to kill myself.",
            "messages": [],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "refused"
    assert data["refusal_category"] == "self_harm"
    assert data["flagged_for_review"] is True


def test_agreement_endpoint_refuses_prohibited_history(client):
    r = client.post(
        "/api/agreements/generate",
        json={
            "user_id": "u1",
            "listing_id": "l1",
            "counterparty_listing_id": "l2",
            "messages": [
                {"role": "user", "content": "Trading cocaine for a bike."},
                {"role": "assistant", "content": "..."},
            ],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "refused"
    assert data["refusal_category"] == "drugs"
