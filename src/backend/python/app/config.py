import os
from typing import List


class Settings:
    APP_NAME = "AntBarter AI Backend"
    APP_VERSION = "1.0.0"

    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    # Cost-friendly default (good enough for negotiation + drafts)
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307")

    # Example Azure SQL URL:
    # mssql+pyodbc://username:password@server.database.windows.net/antbarter?driver=ODBC+Driver+18+for+SQL+Server
    DATABASE_URL = os.getenv("DATABASE_URL", "")

    # --- Usage guardrails (per user_id) ---
    AI_MAX_REQUESTS_PER_DAY = int(os.getenv("AI_MAX_REQUESTS_PER_DAY", "20"))
    AI_MAX_REQUESTS_PER_MONTH = int(os.getenv("AI_MAX_REQUESTS_PER_MONTH", "200"))

    # Rough token estimation (approximate; avoids extra deps).
    # If you want stricter accounting, add true token counting later.
    AI_MAX_OUTPUT_TOKENS = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "350"))
    AI_MAX_INPUT_CHARS = int(os.getenv("AI_MAX_INPUT_CHARS", "4000"))

    # If set (>0), deny requests once monthly estimated tokens exceed this cap.
    AI_MONTHLY_TOKEN_BUDGET = int(os.getenv("AI_MONTHLY_TOKEN_BUDGET", "60000"))

    # --- CORS (avoid credentials + wildcard together; see main.py) ---
    # Comma-separated origins, e.g. https://app.example.com,https://www.example.com
    # Empty string = allow any origin for development only (not recommended for production).
    CORS_ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "")
    CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() in (
        "1",
        "true",
        "yes",
    )

    # --- Meta Content Library: Facebook Marketplace preview (research / approved access only) ---
    # See: https://developers.facebook.com/docs/content-library-and-api/content-library-api/guides/fb-marketplace/
    META_CONTENT_LIBRARY_ENABLED = os.getenv(
        "META_CONTENT_LIBRARY_ENABLED", "false"
    ).lower() in ("1", "true", "yes")
    META_MARKETPLACE_MAX_QUERY_LEN = int(os.getenv("META_MARKETPLACE_MAX_QUERY_LEN", "200"))
    # Optional HTTP fallback when the official Python client is not installed (set by your Meta-approved environment).
    META_CONTENT_LIBRARY_HTTP_BASE_URL = os.getenv("META_CONTENT_LIBRARY_HTTP_BASE_URL", "")
    META_CONTENT_LIBRARY_ACCESS_TOKEN = os.getenv("META_CONTENT_LIBRARY_ACCESS_TOKEN", "")

    # Agreement drafts when the client omits jurisdiction
    DEFAULT_AGREEMENT_JURISDICTION = os.getenv("DEFAULT_AGREEMENT_JURISDICTION", "")

    def cors_origins_list(self) -> List[str]:
        raw = (self.CORS_ALLOW_ORIGINS or "").strip()
        if not raw:
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]


settings = Settings()
