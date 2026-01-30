import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text # <-- NEW IMPORT
from database import add_ticker, get_user_watchlist

# 0. CONFIG & SECRETS
st.set_page_config(page_title="Market Sentinel", layout="wide")
load_dotenv()

# --- DATABASE ENGINE (SQLAlchemy) ---
# This creates a robust connection pool (better than raw psycopg2)
def get_engine():
    try:
        # We need to ensure the URL starts with postgresql://
        db_url = os.getenv("DATABASE_URL")
        if db_url and db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return create_engine(db_url)
    except Exception as e:
        st.error(f"❌ Connection Failed: {e}")
        return None

# --- SIDEBAR: USER PROFILE & WATCHLIST ---
st.title("🤖 AI-Powered Market Sentinel")
st.sidebar.header("👤 User Profile")
user_id = st.sidebar.text_input("Enter Username", value="guest").lower().strip()

st.sidebar.subheader("Manage Watchlist")
new_ticker = st.sidebar.text_input("Add Stock Ticker (e.g. NVDA, ^NSEI)")

if st.sidebar.button("➕ Add to Watchlist"):
    if new_ticker:
        if add_ticker(user_id, new_ticker):
            st.sidebar.success(f"Tracked {new_ticker}!")
            st.rerun()
        else:
            st.sidebar.warning("Could not add ticker.")
    else:
        st.sidebar.error("Please enter a symbol.")

# --- MAIN DASHBOARD LOGIC ---
user_tickers = get_user_watchlist(user_id)

if not user_tickers:
    st.info(f"👋 Hi {user_id}! Your watchlist is empty. Add a stock in the sidebar to start tracking.")
else:
    engine = get_engine()
    if engine:
        # SQLAlchemy requires named parameters (smarter security)
        # We fetch ALL logs for the user's tickers
        if len(user_tickers) == 1:
            query = text("SELECT * FROM market_log WHERE ticker = :ticker ORDER BY timestamp ASC")
            params = {"ticker": user_tickers[0]}
        else:
            query = text("SELECT * FROM market_log WHERE ticker IN :tickers ORDER BY timestamp ASC")
            params = {"tickers": tuple(user_tickers)}
            
        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params=params)

        if not df.empty:
            selected_ticker = st.selectbox("Select Asset to Analyze", user_tickers)
            stock_data = df[df['ticker'] == selected_ticker]
            
            if not stock_data.empty:
                latest = stock_data.iloc[-1]
                
                # --- NEW: PREDICTION MODULE ---
                from prediction_engine import predict_next_day_price
                
                # Calculate Prediction
                predicted_price, signal = predict_next_day_price(selected_ticker, stock_data)

                # --- METRICS ROW ---
                c1, c2, c3, c4 = st.columns(4) # Changed to 4 columns
                
                c1.metric("Current Price", f"{latest['price']:,.2f}")
                
                # Sentiment Color Logic
                sent_color = "normal"
                if latest['sentiment'] == 'positive': sent_color = "off"
                elif latest['sentiment'] == 'negative': sent_color = "inverse"
                
                c2.metric("AI Sentiment", latest['sentiment'].upper(), f"{latest['confidence']:.2f} conf", delta_color=sent_color)
                
                c3.markdown(f"**Latest News:**\n_{latest['headline']}_")
                
                # Prediction Metric (Only shows if we have enough data)
                if predicted_price:
                    delta = predicted_price - latest['price']
                    c4.metric("AI Forecast (24h)", f"{predicted_price:,.2f}", signal)
                else:
                    c4.metric("AI Forecast", "Waiting for Data", "Need 5 Days History", delta_color="off")

                # --- CHART ---
                st.subheader(f"📉 {selected_ticker} Performance")
                fig = go.Figure()
                
                # 1. Historical Price Line
                fig.add_trace(go.Scatter(x=stock_data['timestamp'], y=stock_data['price'], name="Price", line=dict(color='#2962FF', width=3)))
                
                # 2. Prediction Dot (The Future)
                if predicted_price:
                    last_time = stock_data['timestamp'].max()
                    # Add 1 day to the last timestamp
                    future_time = last_time + pd.Timedelta(days=1)
                    
                    fig.add_trace(go.Scatter(
                        x=[last_time, future_time], 
                        y=[latest['price'], predicted_price],
                        name="AI Forecast",
                        line=dict(color='#FFD700', width=2, dash='dot'),
                        marker=dict(size=8, symbol='star')
                    ))

                # 3. Sentiment Bars
                def get_visual_score(row):
                    val = row['confidence']
                    return val if row['sentiment'] == 'positive' else -val if row['sentiment'] == 'negative' else 0

                stock_data['visual_score'] = stock_data.apply(get_visual_score, axis=1)
                
                fig.add_trace(go.Bar(
                    x=stock_data['timestamp'],
                    y=stock_data['visual_score'],
                    name="Sentiment Strength",
                    yaxis="y2",
                    marker_color=stock_data['visual_score'].apply(lambda x: '#00C853' if x > 0 else '#D50000'),
                    opacity=0.4
                ))

                fig.update_layout(
                    template="plotly_dark",
                    yaxis=dict(title="Stock Price"),
                    yaxis2=dict(title="AI Confidence", overlaying="y", side="right", range=[-1.1, 1.1]),
                    hovermode="x unified",
                    legend=dict(orientation="h", y=1.1)
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # ... table code remains the same ...
                with st.expander("📂 View Historical Data Logs"):
                    st.dataframe(stock_data.sort_values(by='timestamp', ascending=False))
            else:
                st.warning(f"You track {selected_ticker}, but no data fetched yet. Run 'main.py'!")
        else:
            st.warning("No data in cloud DB. Run 'main.py'!")