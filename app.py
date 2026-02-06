# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from database import get_latest_data, fetch_all_watchlist_data, get_portfolio_summary
from prediction_engine import predict_next_day_price
from market_utils import get_market_indices

# --- CONFIGURATION ---
st.set_page_config(page_title="Market Sentinel Command Center", layout="wide")

# Initialize Session State
if 'selected_ticker' not in st.session_state:
    st.session_state.selected_ticker = None

# ==========================================
# 🟢 PART 1: GLOBAL MARKET TAPE (Always Visible)
# ==========================================
st.title("🤖 Market Sentinel Command Center")

indices = get_market_indices()
if indices:
    # Dynamic columns based on how many indices we found
    cols = st.columns(len(indices))
    for i, idx in enumerate(indices):
        # Color logic: Green if positive, Red if negative
        color = "normal" if idx['Change'] >= 0 else "inverse"
        cols[i].metric(
            label=idx['Index'],
            value=f"{idx['Price']:,.0f}",
            delta=f"{idx['Change']:.2f}%",
            delta_color=color
        )
st.markdown("---")

# ==========================================
# 🟡 PART 2: THE DASHBOARD LOGIC
# ==========================================

# CONDITION A: SHOW THE GRID (If no ticker is selected)
if st.session_state.selected_ticker is None:
    st.subheader("📊 Your Watchlist Overview")
    
    # Fetch latest data for all stocks
    portfolio = get_portfolio_summary()
    
    if not portfolio:
        st.info("Your portfolio is empty. Run 'main.py' to fetch data!")
    else:
        # Create a Grid (4 cards per row)
        cols = st.columns(4)
        for i, stock in enumerate(portfolio):
            col = cols[i % 4]
            
            with col:
                # Determine Color Scheme based on Sentiment
                sentiment_color = "normal" # Gray/Default
                if stock['sentiment'] == 'positive': sentiment_color = "off" # Green
                elif stock['sentiment'] == 'negative': sentiment_color = "inverse" # Red
                
                # Render Card
                with st.container(border=True):
                    st.metric(
                        label=stock['ticker'],
                        value=f"{stock['price']}",
                        delta=f"{stock['sentiment'].upper()} ({stock['confidence']:.2f})",
                        delta_color=sentiment_color
                    )
                    
                    # The "Analyze" Button
                    if st.button(f"🔍 Deep Dive", key=f"btn_{stock['ticker']}"):
                        st.session_state.selected_ticker = stock['ticker']
                        st.rerun()

# CONDITION B: SHOW THE DEEP DIVE (If a ticker IS selected)
else:
    selected_ticker = st.session_state.selected_ticker
    
    # 🔙 Back Button
    if st.button("⬅️ Back to Dashboard"):
        st.session_state.selected_ticker = None
        st.rerun()
        
    st.markdown(f"## 🔎 Deep Dive Analysis: {selected_ticker}")
    
    # --- FETCH DETAILED DATA ---
    latest = get_latest_data(selected_ticker)
    stock_data = fetch_all_watchlist_data(selected_ticker)
    
    if not latest:
        st.error("No data found for this ticker.")
    else:
        # --- 1. PREDICTION MODULE (Phase 6) ---
        predicted_price, signal = predict_next_day_price(selected_ticker, stock_data)

        # --- 2. METRICS ROW ---
        c1, c2, c3, c4 = st.columns(4)
        
        c1.metric("Current Price", f"{latest['price']:,.2f}")
        
        # Sentiment Styling
        sent_color = "normal"
        if latest['sentiment'] == 'positive': sent_color = "off"
        elif latest['sentiment'] == 'negative': sent_color = "inverse"
        
        c2.metric("AI Sentiment", latest['sentiment'].upper(), f"{latest['confidence']:.2f} conf", delta_color=sent_color)
        c3.markdown(f"**Latest Headline:**\n_{latest['headline']}_")
        
        # Prediction Metric
        if predicted_price:
            c4.metric("AI Forecast (24h)", f"{predicted_price:,.2f}", signal)
        else:
            c4.metric("AI Forecast", "Gathering Data...", "Need 5 Days History", delta_color="off")

        # --- 3. CHARTING ---
        st.subheader(f"📉 Price vs Sentiment Correlation")
        fig = go.Figure()
        
        # Line: Price
        fig.add_trace(go.Scatter(x=stock_data['timestamp'], y=stock_data['price'], name="Price", line=dict(color='#2962FF', width=3)))
        
        # Dot: Prediction
        if predicted_price:
            last_time = stock_data['timestamp'].max()
            future_time = last_time + pd.Timedelta(days=1)
            fig.add_trace(go.Scatter(
                x=[last_time, future_time], 
                y=[latest['price'], predicted_price],
                name="AI Forecast",
                line=dict(color='#FFD700', width=2, dash='dot'),
                marker=dict(size=8, symbol='star')
            ))

        # Bars: Sentiment
        # Helper to visualize sentiment as positive/negative bars
        def get_visual_score(row):
            val = row['confidence']
            return val if row['sentiment'] == 'positive' else -val if row['sentiment'] == 'negative' else 0

        stock_data['visual_score'] = stock_data.apply(get_visual_score, axis=1)
        
        fig.add_trace(go.Bar(
            x=stock_data['timestamp'],
            y=stock_data['visual_score'],
            name="Sentiment Intensity",
            yaxis="y2",
            marker_color=stock_data['visual_score'].apply(lambda x: '#00C853' if x > 0 else '#D50000'),
            opacity=0.4
        ))

        fig.update_layout(
            template="plotly_dark",
            yaxis=dict(title="Stock Price"),
            yaxis2=dict(title="Sentiment Score", overlaying="y", side="right", range=[-1.1, 1.1]),
            hovermode="x unified",
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- 4. DATA TABLE ---
        st.dataframe(stock_data.sort_values(by='timestamp', ascending=False))