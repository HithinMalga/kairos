"""
Kairos - API Layer
Serves the latest scored leaderboard and per-ticker details over HTTP.

Run locally:
    pip install fastapi uvicorn
    uvicorn src.api.main:app --reload

Then visit http://127.0.0.1:8000/docs for interactive API docs.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from db import get_connection

app = FastAPI(
    title="Kairos API",
    description="The right stock, at the right moment. Informational insights only — not financial advice.",
    version="0.1.0",
)

# Allow the frontend (running on a different port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "name": "Kairos API",
        "tagline": "The right stock, at the right moment.",
        "disclaimer": "This tool provides informational, data-driven analytics only. It is not financial advice.",
    }


@app.get("/stocks")
def get_leaderboard(limit: int = 25):
    """Return the latest score for every ticker, ranked highest first."""
    conn = get_connection()
    cur = conn.cursor()

    # Get the most recent score per ticker
    cur.execute("""
        SELECT s.ticker, s.score, s.reason, s.computed_at,
               p.price, p.change_1d, p.change_7d, p.change_30d
        FROM scores s
        JOIN price_snapshots p ON p.ticker = s.ticker
        WHERE s.id IN (
            SELECT MAX(id) FROM scores GROUP BY ticker
        )
        AND p.id IN (
            SELECT MAX(id) FROM price_snapshots GROUP BY ticker
        )
        ORDER BY s.score DESC
        LIMIT ?
    """, (limit,))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No scored data yet. Run the ingestion + scoring pipeline first.")

    return {
        "disclaimer": "Informational only — not financial advice.",
        "count": len(rows),
        "stocks": [dict(row) for row in rows],
    }


@app.get("/stocks/{ticker}")
def get_stock_detail(ticker: str):
    """Return full detail for a single ticker: latest score, price history, headlines."""
    ticker = ticker.upper()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT ticker, score, reason, computed_at FROM scores
        WHERE ticker = ? ORDER BY computed_at DESC LIMIT 1
    """, (ticker,))
    score_row = cur.fetchone()

    if not score_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"No data found for ticker '{ticker}'.")

    cur.execute("""
        SELECT price, change_1d, change_7d, change_30d, volume, avg_volume_10d, fetched_at
        FROM price_snapshots WHERE ticker = ? ORDER BY fetched_at DESC LIMIT 1
    """, (ticker,))
    price_row = cur.fetchone()

    cur.execute("""
        SELECT title, source, url, published_at FROM headlines
        WHERE ticker = ? ORDER BY published_at DESC LIMIT 8
    """, (ticker,))
    headlines = cur.fetchall()

    cur.execute("""
        SELECT date, close FROM price_history
        WHERE ticker = ? ORDER BY date ASC
    """, (ticker,))
    history = cur.fetchall()

    conn.close()

    return {
        "ticker": ticker,
        "score": score_row["score"],
        "reason": score_row["reason"],
        "price": dict(price_row) if price_row else None,
        "headlines": [dict(h) for h in headlines],
        "price_history": [dict(h) for h in history],
        "disclaimer": "Informational only — not financial advice.",
    }
