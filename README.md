Ingestion and scoring are decoupled from the UI — the dashboard just reads the latest
scored data from SQLite, so slow API calls never block the page from loading.

## Setup

```bash
pip install -r requirements.txt
```

## Run the pipeline

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

Opens automatically at http://localhost:8501. From there, a **🔄 Refresh Data Now**
button reruns the full pipeline without touching the terminal again.

## Dashboard features

- **Ranked leaderboard** — all tracked stocks sorted by score
- **Search & sector filter** — narrow down by ticker or sector
- **Sparkline charts** — 30-day price trend per stock, at a glance
- **Clickable headlines** — expand any stock to see its recent news with links
- **One-click refresh** — reruns prices → news → scoring straight from the UI
- **Last updated timestamp** — always visible so you know how fresh the data is

## (Optional) Run the API

```bash
uvicorn src.api.main:app --reload
```

Visit http://127.0.0.1:8000/docs for interactive API docs.
Endpoints: `GET /stocks` (leaderboard), `GET /stocks/{ticker}` (detail + price history + headlines).

## How scoring works

Each stock gets a 0-100 score from three weighted signals:

| Signal | Weight | What it measures |
|---|---|---|
| Momentum | 55% | Blended 1-day / 7-day / 30-day price change |
| Volume | 30% | Today's volume vs. 10-day average (spikes suggest conviction) |
| News | 15% | Recent headline count (more coverage = more market attention) |

## Data notes

- Price/volume data via `yfinance`, ~15-20 min delayed — fine for daily trend
  analysis, not for high-frequency trading
- News headlines via `yfinance`'s built-in news feed
- Storage: SQLite (`data/kairos.db`)

## Deploying publicly (optional)

[Streamlit Community Cloud](https://share.streamlit.io) offers free hosting:
1. Push this repo to GitHub (already done ✅)
2. Go to share.streamlit.io and connect this repo
3. Set the main file path to `src/dashboard.py`
4. Deploy — you'll get a shareable public URL
