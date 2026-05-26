# 🤖 Lucy AI: Predictive Market Intelligence & Agentic Router

Lucy AI is a full-stack machine learning ecosystem for real-time market analysis and intent classification. It runs as a FastAPI service with an **HTMX + Jinja2** dashboard, a Scikit-Learn SVC pipeline, and amCharts 5 visualizations.

## 🚀 Key Features

- **Intent Intelligence**: Scikit-Learn SVC pipeline that classifies user queries with strong accuracy and confidence scores.
- **Predictive Market Insights**: Identifies bullish/bearish trends using historical stock data via Lucy Brain logic.
- **Modernized Infrastructure**: Joblib pipelines for Python 3.10+ compatibility.
- **Dynamic Visualization**: Financial charts powered by amCharts 5 with real-time polling and insight overlays.
- **Scalable Routing**: Agent router for Web3-ready requests with probability-based guardrails.

## 🛠️ Tech Stack

- **FastAPI** — API and server-rendered UI
- **Jinja2 + HTMX** — Dashboard templates and partial updates
- **SQLAlchemy** — Data persistence
- **Scikit-Learn** — Feature engineering and Linear SVM classification
- **amCharts 5** — Time-series charts (CDN)
- **Tailwind CSS** — Utility styling (CDN)

## 📂 Project Structure

```
main.py              # FastAPI app entry point
routers/             # API + page routes
templates/           # Jinja2 HTML
static/              # CSS, JS, assets
brain.py             # Market analysis logic
models/              # Serialized pipelines & vocabularies
demos/               # Training / evaluation scripts
```

## 🛠️ Installation & Setup

1. **Install dependencies**

```bash
pip install -r requirements.txt
```

2. **Configure environment**

```bash
cp env.example .env
# Edit .env with GEMINI_API_KEY and optional Bright Data keys
```

3. **Migrate schema and seed tokens** (adds `token_map.chain` on existing MySQL DBs)

```bash
python migrate_db.py
python seed_data.py
```

`seed_data.py` runs the migration automatically. Re-run seeding after deploy to refresh `address` and `chain` from CoinGecko.

4. **Run the server**

```bash
uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) for the dashboard. JSON APIs are under `/api/market` and `/api/agent`.

For serverless deployment, use `main.handler` (Mangum) as the ASGI entry point.

## 👨‍💻 Recruitment & Business Inquiries

This project demonstrates **legacy modernization, MLOps deployment,** and **full-stack financial dashboarding**.
