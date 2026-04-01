from app import config
from app.marketplace_library import fetch_marketplace_preview_context


def test_marketplace_preview_returns_none_when_disabled(monkeypatch):
    monkeypatch.setattr(config.settings, "META_CONTENT_LIBRARY_ENABLED", False)
    assert (
        fetch_marketplace_preview_context(q="laptop", listing_country_iso2="US") is None
    )


def test_marketplace_preview_returns_none_when_query_empty(monkeypatch):
    monkeypatch.setattr(config.settings, "META_CONTENT_LIBRARY_ENABLED", True)
    assert fetch_marketplace_preview_context(q="", listing_country_iso2=None) is None
