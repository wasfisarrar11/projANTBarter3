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
    assert "ANTHROPIC_API_KEY" in data["ai_response"] or "not configured" in data["ai_response"]
