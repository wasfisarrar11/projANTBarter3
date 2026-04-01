# projANTBarter3 — AntBarter AI

AB Web Application Project.

## Project Direction

This project is now structured to move from a static/manual barter website into an AI-powered negotiation platform that can:
- automatically negotiate trade terms through chat,
- generate a binding barter agreement draft,
- persist sessions and agreements in Azure SQL.

## Tech Stack

- Frontend: HTML/CSS/JavaScript (existing pages retained)
- Backend: Python (FastAPI; Flask is an alternative in the same ecosystem)
- Database: Azure SQL Server
- AI: Claude API (Anthropic)

## Backend Setup (FastAPI)

1. Go to backend folder:
   - `cd src/backend/python`
2. Create and activate venv:
   - `python -m venv .venv`
   - Windows PowerShell: `.venv\Scripts\Activate.ps1`
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Configure env:
   - copy `.env.example` to `.env`
   - set `ANTHROPIC_API_KEY` and `DATABASE_URL` (Azure SQL)
5. Run API:
   - `uvicorn app.main:app --reload --port 8000`

## Frontend Integration

- Updated page: `src/frontend/pages/AB_Home_UI2_Update.html`
- New AI script: `src/frontend/js/AB_ai_chatbot.js`
- New AI UI styles: `src/frontend/css/AB_home2_update.css`

The frontend calls:
- `POST /api/ai/negotiate`
- `POST /api/agreements/generate`
