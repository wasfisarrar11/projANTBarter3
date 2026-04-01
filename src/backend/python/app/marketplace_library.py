"""
Optional Facebook Marketplace listing preview context via Meta Content Library API.

Uses the documented path `facebook/marketplace-listings/preview` and parameters such as
`q` (keyword) and `listing_countries` (ISO Alpha-2), per Meta's guide:
https://developers.facebook.com/docs/content-library-and-api/content-library-api/guides/fb-marketplace/

Access is restricted to approved Meta Content Library / research environments; credentials
must never be exposed to the browser — only server-side env vars.
"""

from __future__ import annotations

import logging
from typing import Any

from .config import settings

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 1200


def _summarize_preview_payload(data: Any) -> str:
    """Reduce API JSON to a short neutral hint for the model (titles/snippets only)."""
    if not data:
        return ""
    lines: list[str] = []
    try:
        if isinstance(data, dict):
            items = (
                data.get("data")
                or data.get("items")
                or data.get("results")
                or data.get("preview")
                or []
            )
            if isinstance(items, list):
                for row in items[:8]:
                    if not isinstance(row, dict):
                        continue
                    title = row.get("title")
                    if title is None and isinstance(row.get("listing_details"), dict):
                        title = row["listing_details"].get("title")
                    title = (str(title) if title else "").strip()
                    if title:
                        lines.append(f"- {title[:200]}")
        elif isinstance(data, list):
            for row in data[:8]:
                if isinstance(row, dict):
                    t = str(row.get("title", "")).strip()[:200]
                    if t:
                        lines.append(f"- {t}")
    except Exception:
        logger.debug("Unexpected marketplace preview JSON shape", exc_info=True)
        return ""
    if not lines:
        return ""
    out = "Public listing titles (sample, not verified): " + " ".join(lines)
    return out[:MAX_CONTEXT_CHARS]


def fetch_marketplace_preview_context(
    *,
    q: str | None,
    listing_country_iso2: str | None,
) -> str | None:
    """
    Return a short text block for prompt augmentation, or None if disabled / unavailable.
    """
    if not settings.META_CONTENT_LIBRARY_ENABLED:
        return None
    if not q or not str(q).strip():
        return None

    q_clean = str(q).strip()[: settings.META_MARKETPLACE_MAX_QUERY_LEN]
    country = None
    if listing_country_iso2 and len(str(listing_country_iso2).strip()) == 2:
        country = str(listing_country_iso2).strip().upper()

    # 1) Official client (distributed in Meta-approved research environments)
    try:
        from metacontentlibraryapi import MetaContentLibraryAPIClient as Client

        Client.set_default_version(Client.LATEST_VERSION)
        params: dict[str, Any] = {"q": q_clean}
        if country:
            params["listing_countries"] = [country]
        response = Client.get(
            path="facebook/marketplace-listings/preview",
            params=params,
        )
        payload: Any
        if hasattr(response, "json"):
            payload = response.json()
            if callable(payload):
                payload = payload()
        else:
            payload = response
        summary = _summarize_preview_payload(payload)
        return summary or None
    except ImportError:
        logger.debug("metacontentlibraryapi not installed; skipping official client.")
    except Exception:
        logger.exception("Meta Content Library client call failed")

    # 2) Optional HTTP fallback (base URL + bearer token from env only)
    base = (settings.META_CONTENT_LIBRARY_HTTP_BASE_URL or "").strip().rstrip("/")
    token = (settings.META_CONTENT_LIBRARY_ACCESS_TOKEN or "").strip()
    if not base or not token:
        return None

    try:
        import httpx

        url = f"{base}/facebook/marketplace-listings/preview"
        params: dict[str, Any] = {"q": q_clean}
        if country:
            params["listing_countries"] = country
        with httpx.Client(timeout=20.0) as client:
            r = client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()
            summary = _summarize_preview_payload(r.json())
            return summary or None
    except Exception:
        logger.exception("Meta Content Library HTTP preview failed")
        return None
