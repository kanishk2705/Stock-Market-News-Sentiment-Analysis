# app.py
from datetime import date
from html import escape

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- IMPORTS ---
from database import (
    get_latest_data, get_portfolio_summary, fetch_unified_data,
    sign_in_user, sign_up_user, logout_user,
    get_user_watchlist, add_ticker_to_watchlist, remove_ticker_from_watchlist,
    backfill_new_stock, _get_secret
)
from prediction_engine import predict_next_day_price
from market_utils import get_market_indices, search_yahoo_finance, get_currency_symbol
from analysis_engine import calculate_technical_indicators, get_market_signal
from ai_analyst import generate_market_briefing
from backtest_engine import run_backtest, verdict, candidate_models, COST_PER_TRADE
from prediction_engine import PRODUCTION_MODEL_NAME

PAGES = ["Dashboard", "🌍 Global Search", "📈 Model Performance"]

# --- CONFIGURATION ---
st.set_page_config(page_title="Market Sentinel", layout="wide", page_icon="🤖")

# Initialize Session State
if 'selected_ticker' not in st.session_state:
    st.session_state.selected_ticker = None
if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'page' not in st.session_state:
    st.session_state['page'] = "Dashboard"


# --- CACHED HELPERS ---
@st.cache_data(ttl=3600, show_spinner=False)
def refresh_history(ticker, day):
    """Tops up missing days of price history at most once per ticker per hour/day."""
    return backfill_new_stock(ticker)


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def cached_briefing(ticker, context_items):
    """One LLM call per ticker per distinct data snapshot (not on every rerun)."""
    return generate_market_briefing(ticker, dict(context_items))


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def cached_prediction(ticker, last_timestamp, n_rows, _df):
    # last_timestamp + n_rows identify the data version; _df itself is not hashed
    return predict_next_day_price(ticker, _df)


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def cached_backtest(ticker, test_days, model_name, last_timestamp, _df):
    model = next(m for m in candidate_models() if m.name == model_name)
    return run_backtest(ticker, _df, model=model, test_days=test_days)


def label_color(label):
    """Green for bullish/positive labels, red for bearish/negative, grey otherwise."""
    text = (label or "").lower()
    if any(k in text for k in ("positive", "bullish", "buy", "oversold", "recovery")):
        return "normal"
    if any(k in text for k in ("negative", "bearish", "sell", "overbought")):
        return "inverse"
    return "off"


def add_and_onboard(ticker):
    """Adds a ticker for the current user and downloads its history."""
    user_id = st.session_state['user'].id
    success, msg = add_ticker_to_watchlist(ticker, user_id)
    if not (success or "Already" in msg):
        st.error(msg)
        return False

    with st.spinner(f"⏳ Downloading history for {ticker}..."):
        ok, backfill_msg = backfill_new_stock(ticker)
    if not ok:
        # Don't leave an unusable ticker in the watchlist
        if success:
            remove_ticker_from_watchlist(ticker, user_id)
        st.error(f"❌ Could not load {ticker}: {backfill_msg}")
        return False
    return True


# ==========================================
# 🔐 AUTHENTICATION & SIDEBAR NAV
# ==========================================
with st.sidebar:
    st.title("🛡️ Sentinel Auth")

    # --- AUTH LOGIC ---
    if st.session_state['user'] is None:
        auth_mode = st.radio("Access Mode", ["Login", "Sign Up"])
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Submit"):
            if auth_mode == "Login":
                response = sign_in_user(email, password)
                if response and response.user:
                    st.session_state['user'] = response.user
                    st.success("✅ Access Granted")
                    st.rerun()
                else:
                    st.error("❌ Invalid Credentials")
            else: # Sign Up
                response = sign_up_user(email, password)
                if response and response.user:
                    st.success("✅ Account Created! Check your email to confirm, then log in.")
                else:
                    st.error("❌ Sign Up Failed (password must be at least 6 characters)")

        demo_email, demo_password = _get_secret("DEMO_EMAIL"), _get_secret("DEMO_PASSWORD")
        if demo_email and demo_password:
            st.info("👀 **Just looking?** Log in with the demo account:\n\n"
                    f"Email: `{demo_email}`  \nPassword: `{demo_password}`")

        st.markdown("---")
        st.warning("⚠️ Please Log In to view the Command Center.")
        st.stop() # 🛑 STOP APP IF NOT LOGGED IN

    # --- LOGGED IN NAV ---
    else:
        st.success(f"👤 {st.session_state['user'].email}")

        # NAVIGATION MENU
        st.markdown("---")
        st.markdown("### 🧭 Navigation")
        page_selection = st.radio("Go to:", PAGES, index=PAGES.index(st.session_state['page']))

        if page_selection != st.session_state['page']:
            st.session_state['page'] = page_selection
            st.rerun()

        st.markdown("---")

        # QUICK ADD (Sidebar)
        with st.expander("⚡ Quick Add Ticker"):
            quick_ticker = st.text_input("Ticker Symbol", placeholder="AAPL")
            if st.button("Add"):
                if add_and_onboard(quick_ticker.strip().upper()):
                    st.session_state['page'] = "Dashboard"
                    st.rerun()

        st.markdown("---")
        if st.button("🚪 Logout", width="stretch"):
            logout_user()
            st.session_state['user'] = None
            st.session_state.selected_ticker = None
            st.rerun()

# ==========================================
# 🌍 PAGE 1: GLOBAL STOCK SEARCH
# ==========================================
if st.session_state['page'] == "🌍 Global Search":
    st.title("🌍 Global Stock Search")
    st.markdown("### Search 100,000+ stocks (US, India, Global)")
    st.info("Type a company name to find its ticker symbol.")

    # 1. The Search Bar
    query = st.text_input("Company Name:", placeholder="Type 'Reliance', 'Tesla', 'HDFC', or 'Apple'...")

    # 2. Dynamic API Fetch
    if query:
        with st.spinner(f"Searching global markets for '{query}'..."):
            results = search_yahoo_finance(query)

        if results:
            st.success(f"Found {len(results)} matches:")

            # 3. Display Results as Cards
            for stock in results:
                c1, c2, c3 = st.columns([3, 1, 1])

                with c1:
                    st.markdown(f"**{stock['name']}**")
                    st.caption(f"Symbol: {stock['symbol']} • Exchange: {stock['exchange']} • Type: {stock['type']}")

                with c2:
                    st.code(stock['symbol'])

                with c3:
                    # Unique key is vital here so buttons don't clash
                    if st.button("➕ Add", key=f"add_{stock['symbol']}"):
                        if add_and_onboard(stock['symbol']):
                            st.toast(f"✅ {stock['symbol']} added!")
                            # Redirect to Dashboard
                            st.session_state['page'] = "Dashboard"
                            st.session_state['selected_ticker'] = None
                            st.rerun()
                st.markdown("---")
        else:
            st.warning("No matches found. Try a specific name.")

# ==========================================
# 📊 PAGE 2: DASHBOARD
# ==========================================
elif st.session_state['page'] == "Dashboard":

    st.title("🤖 Market Sentinel Command Center")

    # Global Market Indices
    indices = get_market_indices()
    if indices:
        cols = st.columns(len(indices))
        for i, idx in enumerate(indices):
            cols[i].metric(label=idx['Index'], value=f"{idx['Price']:,.0f}", delta=f"{idx['Change']:.2f}%")
    st.markdown("---")

    # 1. DATA FOR CURRENT USER ONLY
    user_id = st.session_state['user'].id
    my_tickers = get_user_watchlist(user_id)
    my_portfolio = get_portfolio_summary(my_tickers)

    # CONDITION A: SHOW THE GRID (If no ticker is selected)
    if st.session_state.selected_ticker is None:
        st.subheader("📊 Your Personal Watchlist")

        if not my_portfolio:
            st.info("👋 Welcome! Your watchlist is empty. Go to 'Global Search' in the sidebar to add stocks.")
        else:
            # Create a Grid (4 cards per row)
            cols = st.columns(4)
            for i, stock in enumerate(my_portfolio):
                col = cols[i % 4]

                with col:
                    currency_symbol = get_currency_symbol(stock['ticker'])

                    # Render Card
                    with st.container(border=True):
                        st.metric(
                            label=stock['ticker'],
                            value=f"{currency_symbol}{(stock['price'] or 0):,.2f}",
                            delta=f"{stock['sentiment'].upper()} ({(stock['confidence'] or 0):.2f})",
                            delta_color=label_color(stock['sentiment']), delta_arrow="off"
                        )
                        st.caption(f"as of {str(stock['timestamp'])[:10]}")

                        if st.button("🔍 Deep Dive", key=f"btn_{stock['ticker']}"):
                            st.session_state.selected_ticker = stock['ticker']
                            st.rerun()

    # CONDITION B: SHOW THE DEEP DIVE (If a ticker IS selected)
    else:
        selected_ticker = st.session_state.selected_ticker
        currency_symbol = get_currency_symbol(selected_ticker)

        b1, b2, _ = st.columns([1.2, 1.4, 3])
        if b1.button("⬅️ Back to Dashboard"):
            st.session_state.selected_ticker = None
            st.rerun()
        if b2.button("🗑️ Remove from Watchlist"):
            remove_ticker_from_watchlist(selected_ticker, user_id)
            st.session_state.selected_ticker = None
            st.rerun()

        st.markdown(f"## 🔎 Deep Dive Analysis: {selected_ticker}")

        # --- 1. FETCH & ENRICH DATA ---
        with st.spinner("Syncing latest prices..."):
            refresh_history(selected_ticker, date.today().isoformat())
        stock_data = fetch_unified_data(selected_ticker)

        if stock_data.empty:
            st.error("No data found for this ticker yet. Try removing and re-adding it.")
        else:
            # Calculate Technical Indicators
            stock_data = calculate_technical_indicators(stock_data)
            latest_tech_row = stock_data.iloc[-1]
            tech_signal = get_market_signal(latest_tech_row)
            current_price = float(latest_tech_row['price'])
            st.caption(f"Data as of {latest_tech_row['timestamp']:%d %b %Y} • {len(stock_data):,} trading days")

            # --- 2. PREDICTION MODULE ---
            predicted_price, ai_signal = cached_prediction(
                selected_ticker, str(latest_tech_row['timestamp']), len(stock_data), stock_data)

            # --- 3. GENERATIVE AI BRIEFING ---
            latest = get_latest_data(selected_ticker) or {}
            ai_context = {
                'price': current_price,
                'currency': currency_symbol,
                'rsi': float(latest_tech_row['RSI']),
                'sentiment': latest.get('sentiment') or 'neutral',
                'headline': latest.get('headline') or 'No major news.',
                'prediction': ai_signal if predicted_price else "Wait & See"
            }
            with st.spinner(f"🤖 AI Analyst is reading the news for {selected_ticker}..."):
                briefing = cached_briefing(selected_ticker, tuple(sorted(ai_context.items())))

            st.markdown(f"""
                <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 5px solid #00E676; margin-bottom: 20px;">
                <h4 style="margin-top:0; color: #00E676;">🤖 AI Analyst Verdict</h4>
                <p style="font-size: 1.1em; line-height: 1.6; color: #EEEEEE;">{escape(briefing)}</p>
                </div>
                """, unsafe_allow_html=True)

            # --- 4. METRICS ROW ---
            c1, c2, c3, c4 = st.columns(4)

            c1.metric("Current Price", f"{currency_symbol}{current_price:,.2f}")

            sentiment = ai_context['sentiment']
            c2.metric("News Sentiment", sentiment.upper(), f"{float(latest.get('confidence') or 0):.2f} confidence",
                      delta_color=label_color(sentiment), delta_arrow="off")

            c3.metric("Technical Signal", "RSI: " + f"{latest_tech_row['RSI']:.0f}", tech_signal,
                      delta_color=label_color(tech_signal), delta_arrow="off")

            if predicted_price:
                c4.metric("AI Forecast (24h)", f"{currency_symbol}{predicted_price:,.2f}", ai_signal,
                          delta_color=label_color(ai_signal), delta_arrow="off")
            else:
                c4.metric("AI Forecast", "Unavailable", ai_signal, delta_color="off", delta_arrow="off")

            if latest.get('headline'):
                st.caption(f"📰 Latest headline: {latest['headline']}")
            st.caption("⚠️ The 24h forecast is experimental: in walk-forward backtests it has not beaten a "
                       "naive 'tomorrow = today' forecast. See **📈 Model Performance** for the evidence. Not investment advice.")

            # --- 5. THE PRO CHART (Price + SMA + RSI) ---
            st.subheader("📉 Advanced Market Analysis")

            fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                vertical_spacing=0.03, row_heights=[0.7, 0.3])

            # Row 1: Price & SMAs
            fig.add_trace(go.Scatter(x=stock_data['timestamp'], y=stock_data['price'],
                                     name="Price", line=dict(color='#2962FF', width=2)), row=1, col=1)
            fig.add_trace(go.Scatter(x=stock_data['timestamp'], y=stock_data['SMA_50'],
                                     name="SMA 50", line=dict(color='#FFD700', width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=stock_data['timestamp'], y=stock_data['SMA_200'],
                                     name="SMA 200", line=dict(color='#9C27B0', width=1)), row=1, col=1)

            # Prediction Dot
            if predicted_price:
                last_time = pd.to_datetime(stock_data['timestamp'].iloc[-1])
                future_time = last_time + pd.Timedelta(days=1)
                fig.add_trace(go.Scatter(x=[future_time], y=[predicted_price], name="AI Pred",
                                         mode='markers', marker=dict(size=12, symbol='diamond', color='#00E676')), row=1, col=1)

            # Row 2: RSI
            fig.add_trace(go.Scatter(x=stock_data['timestamp'], y=stock_data['RSI'],
                                     name="RSI", line=dict(color='#FF5252', width=1.5)), row=2, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color="gray", row=2, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="gray", row=2, col=1)

            fig.update_layout(template="plotly_dark", height=600, hovermode="x unified",
                              legend=dict(orientation="h", y=1.04), margin=dict(t=40, b=20))
            st.plotly_chart(fig, width="stretch")

            # --- 6. DATA TABLE ---
            st.dataframe(stock_data.sort_values(by='timestamp', ascending=False), width="stretch")

# ==========================================
# 📈 PAGE 3: MODEL PERFORMANCE (walk-forward backtest)
# ==========================================
elif st.session_state['page'] == "📈 Model Performance":
    st.title("📈 Model Performance")
    st.markdown("How good is the 24h AI forecast really? Each day in the test period is predicted using "
                "**only data available before that day**, then compared with simple baselines.")

    my_tickers = get_user_watchlist(st.session_state['user'].id)
    if not my_tickers:
        st.info("Add stocks to your watchlist first.")
        st.stop()

    c1, c2, c3 = st.columns([1, 2, 1])
    ticker = c1.selectbox("Stock", my_tickers)
    model_names = [m.name for m in candidate_models()]
    model_name = c2.selectbox("Model", model_names, index=model_names.index(PRODUCTION_MODEL_NAME),
                              help="The model used for the 24h forecast is selected by default.")
    periods = {"3 months (63 days)": 63, "6 months (126 days)": 126, "1 year (252 days)": 252}
    test_days = periods[c3.selectbox("Test period", list(periods), index=2)]

    data = fetch_unified_data(ticker)
    if data.empty:
        st.error("No data for this ticker yet.")
        st.stop()

    with st.spinner(f"Running walk-forward backtest for {ticker} (re-training the model every 21 days)..."):
        try:
            result = cached_backtest(ticker, test_days, model_name, str(data['timestamp'].iloc[-1]), data)
        except ValueError as e:
            st.warning(f"Not enough history for this test period: {e}")
            st.stop()
    m, sim = result.metrics, result.frame
    cur = get_currency_symbol(ticker)

    beats = m['skill_vs_naive'] > 0 and m['dm_p_value'] < 0.05
    (st.success if beats else st.warning)(f"**Verdict:** {verdict(m)}")

    # --- 1. FORECAST ACCURACY ---
    st.subheader("🎯 Forecast accuracy")
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Avg. error (MAE) - model", f"{cur}{m['mae_model']:,.2f}",
              f"{m['mae_model'] - m['mae_naive']:+,.2f} vs naive", delta_color="inverse")
    a2.metric("Avg. error - naive (tomorrow = today)", f"{cur}{m['mae_naive']:,.2f}")
    a3.metric("Skill vs naive", f"{m['skill_vs_naive']:+.0%}", "higher is better", delta_color="off", delta_arrow="off",
              help="1 - MAE(model) / MAE(naive). Positive means the model beats the naive forecast.")
    a4.metric("Diebold-Mariano p-value", f"{m['dm_p_value']:.3f}",
              "significant" if m['dm_p_value'] < 0.05 else "not significant", delta_color="off", delta_arrow="off",
              help="Tests whether the model's errors differ from the naive forecast's errors. p < 0.05 = significant.")

    d1, d2, d3 = st.columns(3)
    d1.metric("Direction accuracy - model", f"{m['direction_accuracy']:.1f}%",
              f"{m['direction_accuracy'] - m['always_up_accuracy']:+.1f} pts vs always-up")
    d2.metric("Direction accuracy - 'always up'", f"{m['always_up_accuracy']:.1f}%")
    d3.metric("Days model predicted 'up'", f"{m['predicted_up_share']:.0f}%")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sim['date'], y=sim['actual'], name="Actual", line=dict(color='#2962FF', width=2)))
    fig.add_trace(go.Scatter(x=sim['date'], y=sim['predicted'], name="Model forecast", line=dict(color='#00E676', width=1.5)))
    fig.update_layout(template="plotly_dark", height=380, hovermode="x unified", title="Actual vs. forecast price",
                      legend=dict(orientation="h", y=1.1), margin=dict(t=60))
    st.plotly_chart(fig, width="stretch")

    # --- 2. TRADING SIMULATION ---
    st.subheader("💰 If you had traded the signal")
    st.caption(f"Long for the day when the forecast expected a rise of more than 1%, otherwise in cash. "
               f"{COST_PER_TRADE:.1%} cost per trade.")
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Strategy return", f"{m['strategy_return']:+.1f}%",
              f"{m['strategy_return'] - m['buy_hold_return']:+.1f} pts vs buy & hold")
    t2.metric("Buy & hold return", f"{m['buy_hold_return']:+.1f}%")
    t3.metric("Sharpe ratio (strategy / B&H)", f"{m['strategy_sharpe']:.2f} / {m['buy_hold_sharpe']:.2f}")
    t4.metric("Max drawdown (strategy / B&H)", f"{m['strategy_max_dd']:.1f}% / {m['buy_hold_max_dd']:.1f}%")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sim['date'], y=sim['strategy_equity'], name="Model strategy", line=dict(color='#00E676', width=2)))
    fig.add_trace(go.Scatter(x=sim['date'], y=sim['buy_hold_equity'], name="Buy & hold", line=dict(color='#9E9E9E', width=2)))
    fig.update_layout(template="plotly_dark", height=340, hovermode="x unified", title="Growth of 1 unit invested",
                      legend=dict(orientation="h", y=1.12), margin=dict(t=60))
    st.plotly_chart(fig, width="stretch")
    st.caption(f"{m['trades']} trades • in the market {m['time_in_market']:.1f}% of days • "
               f"{pd.Timestamp(m['start']):%d %b %Y} – {pd.Timestamp(m['end']):%d %b %Y}")

    with st.expander("🔬 Methodology"):
        st.markdown(f"""
- **Walk-forward evaluation:** for each of the last {m['test_days']} trading days, the selected model is trained
  only on data *before* that day and re-trained every 21 days. No future data leaks into any prediction or feature
  (verified by automated tests).
- **Models:** *Random Forest on prices (V2)* learns from raw 60-day price windows. The *returns* models learn
  tomorrow's log return from engineered features (last 5 daily returns, 5/20-day momentum, 20-day volatility, RSI,
  distance from the 50/200-day averages; optionally the FinBERT news-sentiment score) and convert it back to a price.
- **Naive baseline:** tomorrow's price = today's price. For daily stock prices this is a strong baseline that most
  models fail to beat.
- **Diebold-Mariano test:** compares the absolute errors of the model and the naive forecast; p < 0.05 means the
  difference is statistically significant.
- **Direction accuracy** ignores days with no price change. "Always up" is the score of a forecaster that predicts a rise every day.
- **Why V2 failed:** a tree model trained on price *levels* can only output averages of prices it has seen, so it
  cannot follow a stock into a new price range. Learning *returns* removes that limitation.
- **Sentiment data:** news sentiment has only been collected since Jan 2026 (with a gap Jun–Oct 2026), so the
  sentiment model has limited history to learn from.
""")
