# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from database import get_latest_data, fetch_all_watchlist_data, get_portfolio_summary,fetch_price_history,fetch_unified_data
from prediction_engine import predict_next_day_price
from market_utils import get_market_indices
from analysis_engine import calculate_technical_indicators, get_market_signal
from ai_analyst import generate_market_briefing

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
    
   # --- 1. FETCH & ENRICH DATA ---
    stock_data = fetch_unified_data(selected_ticker)
    
    if stock_data.empty:
        st.error("No data found. Please run 'backfill_manager.py' first.")
    else:
        # 🔥 NEW: Calculate Technical Indicators
        stock_data = calculate_technical_indicators(stock_data)
        
        # Get Latest Technical Signal
        latest_tech_row = stock_data.iloc[-1]
        tech_signal = get_market_signal(latest_tech_row)

        # --- 2. PREDICTION MODULE ---
        predicted_price, ai_signal = predict_next_day_price(selected_ticker, stock_data)
             # --- 🔥 NEW: GENERATIVE AI BRIEFING ---
        latest = get_latest_data(selected_ticker)
        if latest:
            with st.spinner(f"🤖 AI Analyst is reading the news for {selected_ticker}..."):
    # Prepare the data packet for the AI
                ai_context = {
                    'price': latest['price'],
                    'rsi': latest_tech_row['RSI'],
                    'sentiment': latest['sentiment'],
                    'headline': latest['headline'],
                    'prediction': ai_signal if predicted_price else "Wait & See"
                }

        # Call Groq
                briefing = generate_market_briefing(selected_ticker, ai_context)

# Display the Briefing
            st.markdown(f"""
                <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 5px solid #00E676; margin-bottom: 20px;">
                <h4 style="margin-top:0; color: #00E676;">🤖 AI Analyst Verdict</h4>
                <p style="font-size: 1.1em; line-height: 1.6;">{briefing}</p>
                </div>
                """, unsafe_allow_html=True)

        # --- 3. METRICS ROW ---
        c1, c2, c3, c4 = st.columns(4)
                
        c1.metric("Current Price", f"${latest['price']:,.2f}")
        
        # Smart Sentiment Color
        sent_color = "normal"
        if latest['sentiment'] == 'positive': sent_color = "off"
        elif latest['sentiment'] == 'negative': sent_color = "inverse"
        c2.metric("News Sentiment", latest['sentiment'].upper(), f"{latest['confidence']:.2f} conf", delta_color=sent_color)
        
        # 🔥 NEW: Technical Signal Card
        c3.metric("Technical Signal", "RSI: " + f"{latest_tech_row['RSI']:.0f}", tech_signal)
        
        if predicted_price:
            c4.metric("AI Forecast (24h)", f"${predicted_price:,.2f}", ai_signal)
        else:
            c4.metric("AI Forecast", "Calculating...", "Need Data", delta_color="off")

        # --- 4. THE PRO CHART (Price + SMA + RSI) ---
        st.subheader(f"📉 Advanced Market Analysis")
        
        # Create a chart with 2 rows (Main Chart + RSI Panel)
        from plotly.subplots import make_subplots
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.03, row_heights=[0.7, 0.3])
        
        # -- ROW 1: PRICE & SMAs --
        # Main Price Line
        fig.add_trace(go.Scatter(x=stock_data['timestamp'], y=stock_data['price'], 
                                 name="Price", line=dict(color='#2962FF', width=2)), row=1, col=1)
        
        # SMA 50 (Yellow)
        fig.add_trace(go.Scatter(x=stock_data['timestamp'], y=stock_data['SMA_50'], 
                                 name="SMA 50", line=dict(color='#FFD700', width=1)), row=1, col=1)
        
        # SMA 200 (Purple)
        fig.add_trace(go.Scatter(x=stock_data['timestamp'], y=stock_data['SMA_200'], 
                                 name="SMA 200", line=dict(color='#9C27B0', width=1)), row=1, col=1)

        # Prediction Dot
        if predicted_price:
            last_time = pd.to_datetime(stock_data['timestamp'].iloc[-1])
            future_time = last_time + pd.Timedelta(days=1)
            fig.add_trace(go.Scatter(x=[future_time], y=[predicted_price], name="AI Pred",
                                     mode='markers', marker=dict(size=12, symbol='diamond', color='#00E676')), row=1, col=1)

        # -- ROW 2: RSI INDICATOR --
        # RSI Line
        fig.add_trace(go.Scatter(x=stock_data['timestamp'], y=stock_data['RSI'], 
                                 name="RSI", line=dict(color='#FF5252', width=1.5)), row=2, col=1)
        
        # RSI Bounds (70 and 30 lines)
        fig.add_hline(y=70, line_dash="dot", line_color="gray", row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="gray", row=2, col=1)

        # Layout Polish
        fig.update_layout(template="plotly_dark", height=600, hovermode="x unified", 
                          legend=dict(orientation="h", y=1.02))
        
        st.plotly_chart(fig, use_container_width=True)
        # --- 4. DATA TABLE ---
        st.dataframe(stock_data.sort_values(by='timestamp', ascending=False))