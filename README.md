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

## The AntBarter AI Backend 
- Checks if the service is running, helps two users negotiate a trade using AI, and can generate a written agreement for their deal
- The negotiation endpoint takes the conversation history and the latest user message, then returns an AI‑generated response
- The agreement endpoint produces a finalized agreement text based on the listings and user IDs involved
