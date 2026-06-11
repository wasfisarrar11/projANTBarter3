import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# Load .env from the python/ directory (one level above this app/ package).
# This runs before any os.getenv() call so all variables are available.
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=False)


class Settings:
    APP_NAME = "AntBarter AI Backend"
    APP_VERSION = "1.0.0"

    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

    DATABASE_URL = os.getenv("DATABASE_URL", "")

    # --- Usage guardrails (per user_id) ---
    AI_MAX_REQUESTS_PER_DAY = int(os.getenv("AI_MAX_REQUESTS_PER_DAY", "20"))
    AI_MAX_REQUESTS_PER_MONTH = int(os.getenv("AI_MAX_REQUESTS_PER_MONTH", "200"))

    AI_MAX_OUTPUT_TOKENS = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "350"))
    AI_MAX_INPUT_CHARS = int(os.getenv("AI_MAX_INPUT_CHARS", "4000"))

    AI_MONTHLY_TOKEN_BUDGET = int(os.getenv("AI_MONTHLY_TOKEN_BUDGET", "60000"))

    # --- Content safety ---
    SAFETY_MODERATION_ENABLED = os.getenv(
        "SAFETY_MODERATION_ENABLED", "true"
    ).lower() in ("1", "true", "yes")
    SAFETY_EXTRA_BLOCKLIST = os.getenv("SAFETY_EXTRA_BLOCKLIST", "")

    # --- Auth ---
    # When True, the AI endpoints require a valid bearer token and the
    # authenticated user_id (sub claim / dev token) overrides whatever the
    # client sent in the request body. When False (default for now so the
    # existing test suite and local development work unchanged) the
    # authenticated user_id is used when present, but absence falls back to
    # the client-supplied value with a warning.
    AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "false").lower() in ("1", "true", "yes")
    # HS256 shared secret. If set, bearer tokens are verified as JWTs with
    # this secret and the `sub` claim is used as user_id. In production with
    # Cognito, swap the implementation in auth.py for a JWKS-based verifier.
    AUTH_JWT_SECRET = os.getenv("AUTH_JWT_SECRET", "")
    AUTH_JWT_ISSUER = os.getenv("AUTH_JWT_ISSUER", "antbarter")
    AUTH_JWT_AUDIENCE = os.getenv("AUTH_JWT_AUDIENCE", "antbarter-api")
    # A simple "dev:<user_id>" token format for local development and tests.
    # NEVER enable in prod.
    AUTH_DEV_TOKENS_ALLOWED = os.getenv(
        "AUTH_DEV_TOKENS_ALLOWED", "true"
    ).lower() in ("1", "true", "yes")

    # --- CORS ---
    CORS_ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "")
    CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() in (
        "1",
        "true",
        "yes",
    )

    # --- Meta Content Library ---
    META_CONTENT_LIBRARY_ENABLED = os.getenv(
        "META_CONTENT_LIBRARY_ENABLED", "false"
    ).lower() in ("1", "true", "yes")
    META_MARKETPLACE_MAX_QUERY_LEN = int(os.getenv("META_MARKETPLACE_MAX_QUERY_LEN", "200"))
    META_CONTENT_LIBRARY_HTTP_BASE_URL = os.getenv("META_CONTENT_LIBRARY_HTTP_BASE_URL", "")
    META_CONTENT_LIBRARY_ACCESS_TOKEN = os.getenv("META_CONTENT_LIBRARY_ACCESS_TOKEN", "")

    DEFAULT_AGREEMENT_JURISDICTION = os.getenv("DEFAULT_AGREEMENT_JURISDICTION", "")

    # --- Stripe subscription billing ---
    # Secret key (sk_test_... in test mode, sk_live_... in live mode). Loaded
    # from env only — never check this into source. The webhook secret is
    # required to verify Stripe is the caller; without it we refuse webhooks.
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    # Public-facing URLs Stripe redirects to after checkout. Must match the
    # production origin (https://yourdomain.com). Leave blank to fall back to
    # the request's Origin header at call time.
    STRIPE_SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL", "")
    STRIPE_CANCEL_URL = os.getenv("STRIPE_CANCEL_URL", "")
    # When true, subscription status gates the AI endpoints. Default false so
    # the existing test suite and free-tier flows keep working until launch.
    BILLING_ENFORCED = os.getenv("BILLING_ENFORCED", "false").lower() in (
        "1",
        "true",
        "yes",
    )

    def cors_origins_list(self) -> List[str]:
        raw = (self.CORS_ALLOW_ORIGINS or "").strip()
        if not raw:
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]


settings = Settings()
