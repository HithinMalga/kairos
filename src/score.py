"""
Kairos - Scoring Engine
Rule-based (no ML) scoring that combines:
  - Price momentum (1d, 7d, 30d % change)
  - Volume spike (today's volume vs 10-day average)
  - News activity (headline count in recent window)
into a single 0-100 score per ticker, plus a plain-English reason.

Run after ingest_prices.py and ingest_news.py:
    python3 src/score.py
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from db import get_connection, init_db

# Weights: momentum matters most, then volume conviction, then news activity
WEIGHT_MOMENTUM = 0.55
WEIGHT_VOLUME = 0.30
WEIGHT_NEWS = 0.15


def normalize(value, low, high):
    """Clamp and scale a value into a 0-100 range."""
    if value is None:
        return 0
    value = max(low, min(high, value))
    return ((value - low) / (high - low)) * 100


def get_latest_snapshot(cur, ticker):
    cur.execute("""
        SELECT * FROM price_snapshots
        WHERE ticker = ?
        ORDER BY fetched_at DESC LIMIT 1
    """, (ticker,))
    return cur.fetchone()


def get_headline_count(cur, ticker):
    cur.execute("SELECT COUNT(*) as c FROM headlines WHERE ticker = ?", (ticker,))
    return cur.fetchone()["c"]


def build_reason(ticker, snap, headline_count, volume_ratio):
    parts = []

    if snap["change_7d"] is not None:
        direction = "up" if snap["change_7d"] >= 0 else "down"
        parts.append(f"{direction} {abs(snap['change_7d']):.1f}% this week")

    if snap["change_1d"] is not None:
        parts.append(f"{snap['change_1d']:+.1f}% today")

    if volume_ratio and volume_ratio >= 1.3:
        parts.append(f"trading at {volume_ratio:.1f}x average volume")

    if headline_count > 0:
        parts.append(f"{headline_count} recent headline{'s' if headline_count != 1 else ''}")

    if not parts:
        return f"{ticker}: not enough recent data to explain movement."

    return f"{ticker} is " + ", with ".join(
        [parts[0]] + [", ".join(parts[1:])] if len(parts) > 1 else parts
    ) + "."


def compute_scores():
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    cur.execute("SELECT DISTINCT ticker FROM price_snapshots")
    tickers = [row["ticker"] for row in cur.fetchall()]

    if not tickers:
        print("No price data found. Run ingest_prices.py first.")
        return

    results = []

    for ticker in tickers:
        snap = get_latest_snapshot(cur, ticker)
        if snap is None:
            continue

        headline_count = get_headline_count(cur, ticker)

        # Momentum score: blend of 1d/7d/30d change, normalized to 0-100
        momentum_raw = (
            (snap["change_1d"] or 0) * 0.2 +
            (snap["change_7d"] or 0) * 0.5 +
            (snap["change_30d"] or 0) * 0.3
        )
        momentum_score = normalize(momentum_raw, -10, 10)

        # Volume score: how much today's volume exceeds the 10-day average
        volume_ratio = None
        if snap["avg_volume_10d"] and snap["avg_volume_10d"] > 0:
            volume_ratio = snap["volume"] / snap["avg_volume_10d"]
        volume_score = normalize(volume_ratio, 0.5, 3.0) if volume_ratio else 0

        # News score: more recent headlines = more market attention
        news_score = normalize(headline_count, 0, 8)

        total_score = round(
            momentum_score * WEIGHT_MOMENTUM +
            volume_score * WEIGHT_VOLUME +
            news_score * WEIGHT_NEWS,
            1
        )

        reason = build_reason(ticker, snap, headline_count, volume_ratio)

        results.append((ticker, total_score, reason))

    # Store scores (clear old score per ticker first so history doesn't pile up)
    for ticker, total_score, reason in results:
        cur.execute("DELETE FROM scores WHERE ticker = ?", (ticker,))
        cur.execute("""
            INSERT INTO scores (ticker, score, reason, computed_at)
            VALUES (?, ?, ?, ?)
        """, (ticker, total_score, reason, now))

    conn.commit()

    # Print ranked leaderboard
    results.sort(key=lambda r: r[1], reverse=True)
    print(f"\n{'Rank':<5}{'Ticker':<8}{'Score':<8}Reason")
    print("-" * 80)
    for i, (ticker, score, reason) in enumerate(results, 1):
        print(f"{i:<5}{ticker:<8}{score:<8}{reason}")

    conn.close()


if __name__ == "__main__":
    compute_scores()
