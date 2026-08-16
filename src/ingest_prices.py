"""
Kairos - Price Ingestion
Pulls recent price/volume history for each ticker via yfinance,
computes % change over 1d/7d/30d and volume vs 10-day average,
then stores a snapshot row per ticker in SQLite.

Run this on your local machine (needs internet access to Yahoo Finance):
    pip install yfinance
    python3 src/ingest_prices.py
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

import yfinance as yf
from tickers import TICKERS
from db import get_connection, init_db


def fetch_and_store():
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    for ticker in TICKERS:
        try:
            # Clear old snapshot + history for this ticker so re-running doesn't pile up duplicates
            cur.execute("DELETE FROM price_snapshots WHERE ticker = ?", (ticker,))
            cur.execute("DELETE FROM price_history WHERE ticker = ?", (ticker,))

            hist = yf.Ticker(ticker).history(period="2mo")
            if hist.empty or len(hist) < 2:
                print(f"[skip] {ticker}: not enough history")
                continue

            # Store daily closes for sparkline charts (last 30 trading days)
            for date_idx, row in hist.tail(30).iterrows():
                cur.execute("""
                    INSERT INTO price_history (ticker, date, close)
                    VALUES (?, ?, ?)
                """, (ticker, str(date_idx.date()), float(row["Close"])))

            latest_price = float(hist["Close"].iloc[-1])
            latest_volume = int(hist["Volume"].iloc[-1])

            def pct_change(days_back):
                if len(hist) <= days_back:
                    return None
                past_price = float(hist["Close"].iloc[-1 - days_back])
                return round(((latest_price - past_price) / past_price) * 100, 2)

            change_1d = pct_change(1)
            change_7d = pct_change(5)   # ~5 trading days = 1 week
            change_30d = pct_change(21)  # ~21 trading days = 1 month

            avg_volume_10d = int(hist["Volume"].tail(10).mean())

            cur.execute("""
                INSERT INTO price_snapshots
                (ticker, price, change_1d, change_7d, change_30d, volume, avg_volume_10d, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ticker, latest_price, change_1d, change_7d, change_30d,
                  latest_volume, avg_volume_10d, now))

            print(f"[ok] {ticker}: ${latest_price:.2f}  1d={change_1d}%  7d={change_7d}%  30d={change_30d}%")

        except Exception as e:
            print(f"[error] {ticker}: {e}")

    conn.commit()
    conn.close()
    print("\nDone. Price snapshots saved to data/kairos.db")


if __name__ == "__main__":
    fetch_and_store()
