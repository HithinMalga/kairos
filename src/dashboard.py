"""
Kairos - Dashboard
Full-featured Streamlit UI: ranked leaderboard, sector filter, search,
sparkline price charts, clickable headlines, and a manual refresh button.

Run locally:
    pip install -r requirements.txt
    streamlit run src/dashboard.py
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

import streamlit as st
from db import get_connection
from tickers import SECTOR_OF

st.set_page_config(page_title="Kairos", page_icon="📈", layout="wide")

# ---------- Header ----------
col_title, col_refresh = st.columns([4, 1])
with col_title:
    st.title("📈 Kairos")
    st.caption("**The right stock, at the right moment.**")
with col_refresh:
    st.write("")
    refresh_clicked = st.button("🔄 Refresh Data Now", use_container_width=True)

st.info(
    "This dashboard shows data-driven insights only — price momentum, volume, and news "
    "activity. It is **not financial advice**, and nothing here should be treated as a "
    "recommendation to buy or sell.",
    icon="ℹ️",
)

# ---------- Refresh pipeline (runs the 3 scripts in sequence) ----------
if refresh_clicked:
    src_dir = Path(__file__).parent
    with st.spinner("Pulling fresh prices, news, and recomputing scores... this can take 20-30 seconds."):
        for script in ["ingest_prices.py", "ingest_news.py", "score.py"]:
            result = subprocess.run(
                [sys.executable, str(src_dir / script)],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                st.error(f"{script} failed:\n{result.stderr}")
                st.stop()
    st.success("Data refreshed!")
    st.cache_data.clear()
    st.rerun()


# ---------- Data loading ----------
@st.cache_data(ttl=60)
def load_leaderboard():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.ticker, s.score, s.reason, s.computed_at,
               p.price, p.change_1d, p.change_7d, p.change_30d
        FROM scores s
        JOIN price_snapshots p ON p.ticker = s.ticker
        WHERE s.id IN (SELECT MAX(id) FROM scores GROUP BY ticker)
        AND p.id IN (SELECT MAX(id) FROM price_snapshots GROUP BY ticker)
        ORDER BY s.score DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


@st.cache_data(ttl=60)
def load_price_history(ticker):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT date, close FROM price_history
        WHERE ticker = ? ORDER BY date ASC
    """, (ticker,))
    rows = cur.fetchall()
    conn.close()
    return {r["date"]: r["close"] for r in rows}


@st.cache_data(ttl=60)
def load_headlines(ticker):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT title, source, url, published_at FROM headlines
        WHERE ticker = ? ORDER BY published_at DESC LIMIT 5
    """, (ticker,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


data = load_leaderboard()

if not data:
    st.warning(
        "No data yet. Click **Refresh Data Now** above, or run the pipeline manually:\n\n"
        "```\npython src/ingest_prices.py\npython src/ingest_news.py\npython src/score.py\n```"
    )
else:
    # ---------- Last updated timestamp ----------
    last_updated = data[0]["computed_at"]
    try:
        dt = datetime.fromisoformat(last_updated)
        friendly_time = dt.strftime("%b %d, %Y at %H:%M UTC")
    except Exception:
        friendly_time = last_updated
    st.caption(f"🕒 Last updated: {friendly_time}")

    # ---------- Filters ----------
    col_search, col_sector = st.columns([2, 1])
    with col_search:
        search_query = st.text_input("🔍 Search by ticker", placeholder="e.g. NVDA")
    with col_sector:
        sector_options = ["All Sectors"] + sorted(set(SECTOR_OF.values()))
        selected_sector = st.selectbox("Filter by sector", sector_options)

    filtered = data
    if search_query:
        filtered = [s for s in filtered if search_query.upper() in s["ticker"]]
    if selected_sector != "All Sectors":
        filtered = [s for s in filtered if SECTOR_OF.get(s["ticker"]) == selected_sector]

    st.subheader(f"Showing {len(filtered)} of {len(data)} Stocks")

    if not filtered:
        st.write("No stocks match your filters.")

    for i, stock in enumerate(filtered, 1):
        ticker = stock["ticker"]
        sector = SECTOR_OF.get(ticker, "—")

        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([0.4, 1.3, 1, 1.6, 3])

            with col1:
                st.markdown(f"### #{i}")

            with col2:
                st.markdown(f"### {ticker}")
                st.caption(f"${stock['price']:.2f} · {sector}")

            with col3:
                st.metric("Score", f"{stock['score']:.1f}")
                change_7d = stock["change_7d"] or 0
                st.caption(f"{'🟢' if change_7d >= 0 else '🔴'} {change_7d:+.1f}% (7d)")

            with col4:
                history = load_price_history(ticker)
                if history:
                    st.line_chart(list(history.values()), height=100)
                else:
                    st.caption("No chart data")

            with col5:
                st.markdown("**Why it's trending:**")
                st.write(stock["reason"])

            with st.expander(f"📰 Recent headlines for {ticker}"):
                headlines = load_headlines(ticker)
                if not headlines:
                    st.caption("No headlines available.")
                for h in headlines:
                    if h["url"]:
                        st.markdown(f"- [{h['title']}]({h['url']}) — *{h['source']}*")
                    else:
                        st.markdown(f"- {h['title']} — *{h['source']}*")

    st.divider()
    st.caption(
        "Scores are computed from price momentum, trading volume vs average, and recent "
        "news activity. Data has a ~15-20 minute delay (Yahoo Finance). "
        "Educational/informational tool only."
    )
