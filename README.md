# Kairos 📈
**The right stock, at the right moment.**

Kairos surfaces which stocks are performing best right now and explains *why*, using
price momentum, trading volume, and recent news activity — no ML, no black box, just
transparent rule-based scoring.

> ⚠️ Informational tool only. Not financial advice.

## Setup

```bash
pip install -r requirements.txt
```

## Run the pipeline (do this first, and any time you want fresh data)

```bash
python src/ingest_prices.py
python src/ingest_news.py
python src/score.py
```

The last command prints a ranked leaderboard directly in your terminal.

## View the dashboard

```bash
streamlit run src/dashboard.py
```

This opens in your browser automatically (usually http://localhost:8501).

## (Optional) Run the API

```bash
uvicorn src.api.main:app --reload
```

Visit http://127.0.0.1:8000/docs for interactive API docs.
Endpoints: `GET /stocks` (leaderboard), `GET /stocks/{ticker}` (detail).

## Dashboard features

- **Ranked leaderboard** — all tracked stocks sorted by score
- **Search & sector filter** — narrow down by ticker or sector (Tech, Finance, Healthcare, Consumer, Energy/Industrial)
- **Sparkline charts** — 30-day price trend per stock, at a glance
- **Clickable headlines** — expand any stock to see its recent news with links
- **Refresh Data Now button** — reruns the full pipeline (prices → news → scoring) directly from the UI, no terminal needed
- **Last updated timestamp** — always visible so you know how fresh the data is

## Deploying publicly (optional)

Streamlit Community Cloud offers free hosting:
1. Push this project to a GitHub repo
2. Go to share.streamlit.io and connect your repo
3. Set the main file path to `src/dashboard.py`
4. Deploy — you'll get a public URL to share

Note: on a public deployment, the "Refresh Data Now" button will pull live data on Streamlit's servers, so make sure your repo includes `requirements.txt` (it does).

## How scoring works

Each stock gets a 0-100 score from three weighted signals:
- **Momentum (55%)** — blended 1-day/7-day/30-day price change
- **Volume (30%)** — today's volume vs. 10-day average (spikes suggest conviction)
- **News (15%)** — recent headline count (more coverage = more market attention)

## Data notes

- Price/volume data via `yfinance` (Yahoo Finance), ~15-20 min delayed
- News headlines via `yfinance`'s built-in news feed
- Storage: SQLite (`data/kairos.db`)
