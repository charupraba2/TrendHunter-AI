# TrendHunter AI

TrendHunter AI is an enterprise intelligence workspace that turns market signals into executive-ready decisions. It combines search intelligence, product impact prediction, competitor analysis, market opportunity detection, and board-level summaries into one FastAPI application.

## Key Features

- Executive Dashboard
- Search Intelligence
- Product Impact Prediction
- Competitor Intelligence
- Market Opportunities
- AI Insight Engine

## Tech Stack

- FastAPI
- Python
- SQLite
- JavaScript
- Gemini API
- News API
- YouTube API
- Scikit-learn
- Docker
- Render

## What It Does

- Tracks industry and company signals across trends, competitors, and opportunity areas
- Scores market momentum, launch readiness, revenue opportunity, and competitive threat
- Produces concise executive summaries instead of long research reports
- Keeps AI explanations separate from numeric scoring so the logic stays auditable
- Supports local development and Render deployment

## Run Locally

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file from `.env.example`.
5. Start the app:

```bash
py -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

If `py` is not available, use:

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

6. Open:

- App: `http://127.0.0.1:8000`
- Dashboard: `http://127.0.0.1:8000/dashboard`
- Industry Intelligence: `http://127.0.0.1:8000/industry-intelligence`
- Health check: `http://127.0.0.1:8000/health`

## Environment Variables

Required or commonly used variables:

- `SECRET_KEY`
- `DATABASE_URL`
- `ALLOWED_ORIGINS`
- `TRUSTED_HOSTS`
- `GEMINI_API_KEY`
- `NEWS_API_KEY`
- `YOUTUBE_API_KEY`
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`
- `APP_ENV`
- `APP_HOST`
- `APP_PORT`
- `LOG_LEVEL`

## Deployment

- Deployment link: `https://trendhunter-ai-latest.onrender.com`
- Render start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Render config: `render.yaml`

## GitHub Repository

- Repo: `https://github.com/charupraba2/TrendHunter-AI`

## Screenshots

Add screenshots here before final submission.

## Interview-Ready Summary

TrendHunter AI is a full-stack enterprise intelligence platform that helps teams understand market movement, competitor pressure, and product impact in one place. The system uses FastAPI, SQLite, JavaScript, and Scikit-learn to blend analytics scoring with AI explanations, producing concise executive briefs that are easier to act on than raw reports.

## Project Structure

```text
TrendHunter AI/
|-- backend/
|-- database/
|-- models/
|-- static/
|-- templates/
|-- requirements.txt
|-- render.yaml
|-- Dockerfile
|-- README.md
```

## Health Check

```bash
GET /health
```

The health endpoint confirms the app status and whether external API keys are configured.
