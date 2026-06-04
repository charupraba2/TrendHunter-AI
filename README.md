# TrendHunter AI

Real-Time Viral Trend Predictor for Content Creators.

This repository provides a production-style starter scaffold for a FastAPI backend, HTML/CSS/JavaScript frontend templates, SQLite storage, and AI-ready service modules for:

- Reddit trend discovery
- Google Trends ingestion via PyTrends
- Sentiment analysis
- Virality scoring
- AI-assisted content suggestions

## Tech Stack

- Backend: FastAPI
- Frontend: HTML, CSS, JavaScript
- Database: SQLite
- ML: Scikit-learn
- Data Sources: Reddit API, Google Trends via PyTrends
- LLM: Gemini API

## Project Structure

```text
TrendHunter AI/
|-- backend/
|-- frontend/
|-- database/
|-- models/
|-- static/
|-- templates/
|-- requirements.txt
|-- README.md
`-- .env.example
```

## Run Locally

1. Create a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in the values you need.
4. Start the app:

```bash
uvicorn backend.main:app --reload
```

5. Open:

- Landing page: `http://127.0.0.1:8000/`
- Dashboard: `http://127.0.0.1:8000/dashboard`
- Trend details: `http://127.0.0.1:8000/trends/{trend_id}`

## Reddit API Setup

To enable the Reddit Trend Collector Agent, add these values to your `.env` file:

- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`

You can create the Reddit app credentials from your Reddit developer app settings. If the credentials are missing, TrendHunter AI automatically switches to demo mode and saves demo trends to SQLite instead of crashing.

### Fetch Reddit Trends

After starting the server, call:

```bash
GET http://127.0.0.1:8000/api/fetch-reddit-trends
```

This endpoint fetches hot and rising posts from the configured subreddits and stores them in the `trends` table.

## Google Trends Setup

TrendHunter AI uses PyTrends to collect trending search terms for India by default.

### Fetch Google Trends

After starting the server, call:

```bash
GET http://127.0.0.1:8000/api/fetch-google-trends
```

This endpoint stores the latest Google Trends rows in SQLite and returns the collected data as JSON.

### Unified Trends API

The dashboard now reads from:

```bash
GET http://127.0.0.1:8000/api/trends
```

This endpoint returns the latest stored Reddit and Google Trends rows together, including:

- `title`
- `platform`
- `subreddit` when available
- `upvotes` and `comments` when available
- `trend_score` or `search_interest`
- `fetched_at`

Use the dashboard refresh buttons to fetch Reddit trends, fetch Google Trends, or reload the stored feed.

## Real-Time Live Trend Engine

TrendHunter AI now supports a modular live-source pipeline for news and video trends.

### Environment Variables

Add these values to `.env`:

- `NEWS_API_KEY=your_newsapi_key_here`
- `YOUTUBE_API_KEY=your_youtube_api_key_here`
- `GEMINI_API_KEY=your_gemini_api_key_here`

### Live Trend Endpoints

Fetch News trends:

```bash
GET http://127.0.0.1:8000/api/fetch-news-trends
```

Optional keyword search:

```bash
GET http://127.0.0.1:8000/api/fetch-news-trends?keyword=ai
```

Fetch YouTube trends:

```bash
GET http://127.0.0.1:8000/api/fetch-youtube-trends
```

Fetch both sources together:

```bash
GET http://127.0.0.1:8000/api/fetch-live-trends
```

### AI Analysis Endpoint

```bash
GET http://127.0.0.1:8000/api/analyze-trend?title=AI%20Agents&description=Creators%20are%20using%20agents%20to%20automate%20workflows
```

This endpoint returns a Gemini-powered JSON analysis with:

- `trend_summary`
- `why_it_is_trending`
- `virality_explanation`
- `audience_interest`
- `future_prediction`

If an API key is missing, the app automatically uses a demo fallback instead of crashing.

### Dashboard Changes

The dashboard now includes:

- `Fetch Live Trends`
- source badges for `NEWS` and `YOUTUBE`
- a loading animation during fetches
- an AI summary modal for live trend analysis
- success toast notifications for fetched data

## RAG-Based Trend Intelligence

TrendHunter AI now includes a lightweight RAG pipeline that uses stored SQLite trends as historical context for Gemini analysis.

### What RAG Means Here

RAG stands for Retrieval-Augmented Generation. In this project, that means:

1. The app searches previously stored trends in SQLite.
2. It scores how similar they are to the new trend using title, keyword, description, source, and virality signals.
3. The top similar trends are passed to Gemini as context.
4. Gemini returns a trend analysis that is grounded in historical examples.

### RAG Endpoint

```bash
GET http://127.0.0.1:8000/api/rag-analyze-trend?title=AI%20Agents&description=AI%20tools%20are%20automating%20workflows
```

### Response Shape

The endpoint returns:

- `current_trend`
- `similar_trends`
- `rag_analysis`

The `rag_analysis` object includes:

- `summary`
- `historical_comparison`
- `virality_prediction`
- `content_opportunities`
- `risk_level`
- `final_recommendation`

### Dashboard Usage

- Use `RAG Analyze` on the dashboard to generate a historical analysis for a trend.
- The modal shows similar past trends alongside the AI-generated recommendation.

## Live Dashboard WebSockets

TrendHunter AI includes a real-time WebSocket layer so the dashboard can update without refreshing the page.

### WebSocket Endpoint

```bash
ws://127.0.0.1:8000/ws/dashboard
```

Use `wss://` when deploying behind HTTPS.

### What Gets Broadcast

- new trends fetched from Reddit, Google Trends, NewsAPI, and YouTube
- new alerts generated by the alert system
- virality updates after analysis
- RAG analysis completions
- activity feed messages and connection status updates

### Dashboard Live Features

- automatic connection and reconnect handling
- live status indicator
- live activity feed
- live ticker
- online users counter
- optional sound notification for alert events
- real-time updates to trend cards, alerts, and RAG panels

### Deployment Notes

- If you deploy behind a reverse proxy, make sure WebSocket upgrade headers are forwarded.
- Uvicorn with `--reload` is fine for development, but production should use a proper ASGI deployment setup.
- If HTTPS is enabled, the frontend will automatically use `wss://` instead of `ws://`.

## Sentiment and Virality Analysis

TrendHunter AI now includes a rule-based analysis step powered by VADER sentiment scoring and a transparent virality formula.

### Analyze Stored Trends

After fetching Reddit or Google Trends data, call:

```bash
GET http://127.0.0.1:8000/api/analyze-trends
```

This endpoint:

- finds stored trends that have not been analyzed yet
- calculates sentiment scores and labels
- calculates virality scores and labels
- saves the analysis results back into SQLite

### Returned Fields

The unified trends API now includes:

- `sentiment_label`
- `positive_score`
- `negative_score`
- `neutral_score`
- `compound_score`
- `virality_score`
- `virality_label`
- `analyzed_at`

## Gemini Content Ideas

TrendHunter AI can generate structured content ideas for analyzed trends using the Gemini API.

### Environment Variable

Add the following to `.env`:

- `GEMINI_API_KEY=your_gemini_api_key_here`

If the key is missing, the app uses a high-quality demo fallback instead of crashing.

### Generate Content Ideas

After analyzing trends, call:

```bash
GET http://127.0.0.1:8000/api/generate-content-ideas
```

This endpoint stores content ideas in SQLite and returns the generated results.

### Fetch a Saved Content Idea

```bash
GET http://127.0.0.1:8000/api/trend/{trend_id}/content-idea
```

The dashboard can also display saved content ideas in a modal when available.

## Alert Agent

TrendHunter AI includes an alert system for trends that cross the high-viral threshold.

### Generate Alerts

After analyzing trends, call:

```bash
GET http://127.0.0.1:8000/api/generate-alerts
```

This endpoint:

- finds high viral trends that do not already have alerts
- creates alert records in SQLite
- returns the generated alerts

### View Alerts

```bash
GET http://127.0.0.1:8000/api/alerts
```

### Mark an Alert as Read

```bash
POST http://127.0.0.1:8000/api/alerts/{alert_id}/read
```

The dashboard shows alert cards, unread highlighting, and a toast popup when new alerts are generated.

## AI Virality Forecasting Engine

TrendHunter AI now includes a forecasting layer that predicts whether a trend will grow, stabilize, or decline in the next 24 to 48 hours.

### Forecast Inputs

The forecasting service uses:

- historical trends stored in SQLite
- virality scores
- upvotes and comments
- trend age
- source type
- keyword overlap with historical trends
- similarity to previous viral trends

### Prediction Labels

Forecast outputs use these labels:

- `EXPLODING`
- `GROWING`
- `STABLE`
- `DECLINING`
- `SATURATED`

### Forecast API Endpoints

Forecast a single trend:

```bash
GET http://127.0.0.1:8000/api/forecast-trend?title=AI%20Agents&description=AI%20tools%20are%20automating%20workflows
```

Forecast all stored trends:

```bash
GET http://127.0.0.1:8000/api/forecast-live-trends
```

### Response Fields

The forecast payload includes:

- `virality_probability`
- `forecast_confidence`
- `growth_stage`
- `prediction_label`
- `expected_engagement`
- `opportunity_score`
- `risk_score`
- `forecast_updated_at`

### Dashboard Forecast UI

The dashboard now includes:

- an `AI Forecast` button
- forecast summary cards
- a forecast modal
- confidence meters and prediction badges
- live websocket forecast updates

### WebSocket Forecast Updates

When forecast data changes, the backend broadcasts a `forecast_update` event to connected dashboard clients so cards and modals can update without refresh.

Example payload:

```json
{
  "type": "forecast_update",
  "timestamp": "2026-06-04T10:00:00+00:00",
  "active_connections": 2,
  "payload": {
    "action": "updated",
    "trend": {
      "title": "AI Agents",
      "prediction_label": "GROWING",
      "forecast_confidence": 84.2,
      "virality_probability": 0.81
    },
    "forecast": {
      "prediction_label": "GROWING",
      "forecast_confidence": 84.2,
      "virality_probability": 0.81
    }
  }
}
```

### Forecasting Formula

The current engine is rule-based and explainable. It blends:

- engagement strength
- historical similarity
- keyword pressure
- source weighting
- age decay
- sentiment signal
- optional sklearn model output when enough history exists

The result is normalized into a probability-like score, then mapped to the prediction labels above.

### Notes

- Gemini is used for the written explanation when available.
- If Gemini is unavailable or the model cannot be reached, the app falls back to a demo forecast instead of failing.
- The dashboard and websocket layer keep working even if the AI model returns a fallback response.

## Phase 13 UI Redesign

TrendHunter AI now uses the **Emerald Dark Intelligence Theme** for the dashboard and detail views.

### Theme Direction

- Background: near-black charcoal
- Accents: emerald green, amber gold, and subtle purple highlights
- Surfaces: glassmorphism panels with soft blur
- Effects: glow borders, premium shadows, and animated live indicators

### UI Improvements

- redesigned summary cards and intelligence panel
- upgraded forecast badges and modal treatments
- refined alert cards and live activity feed styling
- improved responsive spacing and mobile layout behavior
- darker premium surfaces across the dashboard and trend detail pages

## Notes

- The current backend uses safe placeholder logic so the app runs without external API keys.
- The structure is intentionally modular so the real Reddit, PyTrends, Gemini, ML, and forecasting implementations can be dropped in phase by phase.

## Production Deployment

TrendHunter AI is deployment-ready with Docker, Railway, and Render support.

### Environment Setup

Before deploying, configure these variables:

- `APP_ENV=production`
- `LOG_LEVEL=INFO`
- `ALLOWED_ORIGINS=https://your-domain.com`
- `TRUSTED_HOSTS=your-domain.com`
- `GEMINI_API_KEY`
- `NEWS_API_KEY`
- `YOUTUBE_API_KEY`
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`

Never commit your `.env` file. The repository now ignores it by default.

### Docker Deployment

Build the image:

```bash
docker build -t trendhunter-ai .
```

Run the container:

```bash
docker run -p 8000:8000 --env-file .env trendhunter-ai
```

The container starts with:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

### Railway Deployment

This repo includes `railway.json` with a Docker-based deployment setup.

Steps:

1. Create a new Railway project from the GitHub repo.
2. Add the required environment variables in Railway.
3. Deploy using the included `Dockerfile`.
4. Confirm the app starts with the Railway-provided `PORT`.
5. Check `/health` after deployment.

### Render Deployment

This repo includes `render.yaml` for Render web service deployment.

Steps:

1. Create a new Render Web Service from the GitHub repo.
2. Use the included `render.yaml`.
3. Add all required environment variables in Render.
4. Deploy and verify the start command uses the `PORT` environment variable.
5. Open `/health` and `/dashboard` to confirm the app is working.

### WebSocket Support Notes

- The dashboard uses WebSockets at `/ws/dashboard`.
- Reverse proxies must forward WebSocket upgrade headers.
- Use `wss://` behind HTTPS.
- The live dashboard reconnects automatically after temporary disconnects.

### Troubleshooting

- If the dashboard loads but live updates do not appear, confirm WebSocket support is enabled in your deployment platform.
- If trends fall back to demo data, verify the API keys in your environment variables.
- If `/health` returns a warning state, check the logs for missing keys or host validation issues.
- If the app fails to start in production, ensure the working directory contains `backend/main.py` and `requirements.txt`.

### Production Checklist

- `.env` is not committed
- API keys are configured
- dependencies are installed
- WebSockets are supported by the host
- `/health` returns the enhanced payload
- Docker build succeeds locally
- the dashboard loads at `/dashboard`
- no debug prints remain in the codebase

## Live Dashboard WebSockets

TrendHunter AI includes a real-time WebSocket layer so the dashboard can update without refreshing the page.

### WebSocket Endpoint

```bash
ws://127.0.0.1:8000/ws/dashboard
```

Use `wss://` when deploying behind HTTPS.

The dashboard connects automatically on page load and reconnects if the socket drops.

### What Gets Broadcast

- new trends fetched from Reddit, Google Trends, NewsAPI, and YouTube
- new alerts generated by the alert system
- virality updates after analysis
- RAG analysis completions
- activity feed messages and connection status updates

### Dashboard Live Features

- automatic connection and reconnect handling
- live status indicator
- live activity feed
- live ticker
- online users counter
- optional sound notification for alert events
- real-time updates to trend cards, alerts, and RAG panels

### Example Payloads

Connection status:

```json
{
  "type": "connection_status",
  "timestamp": "2026-06-04T10:00:00+00:00",
  "active_connections": 2,
  "payload": {
    "connected": true,
    "active_connections": 2,
    "message": "Connected to TrendHunter AI live dashboard."
  }
}
```

Trend update:

```json
{
  "type": "trend_update",
  "timestamp": "2026-06-04T10:01:00+00:00",
  "active_connections": 2,
  "payload": {
    "action": "created",
    "trend": {
      "title": "AI Agents",
      "platform": "news",
      "virality_score": 88
    }
  }
}
```

Alert update:

```json
{
  "type": "alert_update",
  "timestamp": "2026-06-04T10:02:00+00:00",
  "active_connections": 2,
  "payload": {
    "action": "created",
    "alert": {
      "title": "AI Agents",
      "virality_score": 88,
      "message": "High viral trend detected..."
    }
  }
}
```

### Deployment Notes

- If you deploy behind a reverse proxy, make sure WebSocket upgrade headers are forwarded.
- Uvicorn with `--reload` is fine for development, but production should use a proper ASGI deployment setup.
- If HTTPS is enabled, the frontend automatically uses `wss://` instead of `ws://`.

