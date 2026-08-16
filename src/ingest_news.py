"""
Kairos - News Ingestion
Pulls recent headlines per ticker using yfinance's built-in news feed
(no separate news API key needed — keeps setup fast for the 2-3 day build).

Run this on your local machine (needs internet access):
    python3 src/ingest_news.py
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
            # Clear old headlines for this ticker first so re-running doesn't pile up duplicates
            cur.execute("DELETE FROM headlines WHERE ticker = ?", (ticker,))

            news_items = yf.Ticker(ticker).news or []
            count = 0

            for item in news_items[:8]:  # cap per ticker to keep it lean
                # yfinance's news schema nests fields under "content" in newer versions
                content = item.get("content", item)
                title = content.get("title")
                if not title:
                    continue

                source = (content.get("provider") or {}).get("displayName", "Unknown")
                url = (content.get("canonicalUrl") or {}).get("url", "")
                published_at = content.get("pubDate", "")

                cur.execute("""
                    INSERT INTO headlines (ticker, title, source, url, published_at, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (ticker, title, source, url, published_at, now))
                count += 1

            print(f"[ok] {ticker}: {count} headlines")

        except Exception as e:
            print(f"[error] {ticker}: {e}")

    conn.commit()
    conn.close()
    print("\nDone. Headlines saved to data/kairos.db")


if __name__ == "__main__":
    fetch_and_store()
