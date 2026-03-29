# Azure App Service + Azure SQL Deployment

This repo’s backend is a FastAPI service designed to run on **Azure App Service (Linux)** and persist data to **Azure SQL**.

## Backend (App Service) - Recommended: Container Deploy

Backend Dockerfile:
- `src/backend/python/Dockerfile`

### App Service settings

In App Service → **Configuration** → **Application settings**, set:
- `ANTHROPIC_API_KEY`
- `CLAUDE_MODEL` (default: `claude-3-haiku-20240307`)
- `DATABASE_URL`
- `AI_MAX_REQUESTS_PER_DAY`
- `AI_MAX_REQUESTS_PER_MONTH`
- `AI_MAX_OUTPUT_TOKENS`
- `AI_MAX_INPUT_CHARS`
- `AI_MONTHLY_TOKEN_BUDGET`

**Important:** App Service sets `PORT` automatically; the container command binds to it.

### DATABASE_URL (Azure SQL)

Use SQLAlchemy + pyodbc format:

`mssql+pyodbc://<user>:<password>@<server>.database.windows.net/<db>?driver=ODBC+Driver+18+for+SQL+Server`

Notes:
- Use a SQL auth user for simplest setup (or add Managed Identity later).
- Ensure firewall allows the App Service outbound IPs (or use Private Endpoint).

## Azure SQL (Basic) Notes

The backend auto-creates tables at startup (`Base.metadata.create_all`).

If your Azure SQL permissions do not allow DDL at runtime, pre-create schema by running the app once with a privileged user, or apply a schema migration strategy later.

## Frontend (Azure Static Web Apps)

Frontend stays as static HTML/CSS/JS. The AI chat calls the backend API:
- `POST /api/ai/negotiate`
- `POST /api/agreements/generate`

In production, set `window.AI_API_BASE_URL` (or edit `AB_ai_chatbot.js`) to your App Service URL.

## Usage guardrails

Guardrails are enforced server-side per `user_id`:
- **Request caps**: daily + monthly limits
- **Token caps**: max output tokens per call + monthly estimated token ceiling
- **Input size cap**: max characters for user messages

Defaults are in `src/backend/python/app/config.py` and `.env.example`.

Tune:
- lower `AI_MAX_OUTPUT_TOKENS` to reduce tokens per request
- lower `AI_MAX_REQUESTS_PER_MONTH` to cap total API usage
- lower `AI_MONTHLY_TOKEN_BUDGET` to enforce a hard monthly token ceiling
