import os


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


settings = Settings()
