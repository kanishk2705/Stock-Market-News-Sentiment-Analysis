# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time

# --- IMPORTS ---
from database import (
    get_latest_data, fetch_all_watchlist_data, get_portfolio_summary, 
    fetch_price_history, fetch_unified_data,
    sign_in_user, sign_up_user, logout_user,
    get_user_watchlist, add_ticker_to_watchlist, backfill_new_stock
)
from prediction_engine import predict_next_day_price
from market_utils import get_market_indices, search_yahoo_finance # <--- Ensure this is in market_utils.py
from analysis_engine import calculate_technical_indicators, get_market_signal
from ai_analyst import generate_market_briefing

# --- CONFIGURATION ---
st.set_page_config(page_title="Market Sentinel", layout="wide", page_icon="🤖")

# Initialize Session State
if 'selected_ticker' not in st.session_state:
    st.session_state.selected_ticker = None
if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'page' not in st.session_state:
    st.session_state['page'] = "Dashboard"

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
                    st.success("✅ Account Created! Please Log In.")
                else:
                    st.error("❌ Sign Up Failed")
        
        st.markdown("---")
        st.warning("⚠️ Please Log In to view the Command Center.")
        st.stop() # 🛑 STOP APP IF NOT LOGGED IN

    # --- LOGGED IN NAV ---
    else:
        st.success(f"👤 {st.session_state['user'].email}")
        
        # NAVIGATION MENU
        st.markdown("---")
        st.markdown("### 🧭 Navigation")
        page_selection = st.radio("Go to:", ["Dashboard", "🌍 Global Search"], 
                                  index=0 if st.session_state['page']=="Dashboard" else 1)
        
        if page_selection != st.session_state['page']:
            st.session_state['page'] = page_selection
            st.rerun()

        st.markdown("---")
        
        # QUICK ADD (Sidebar)
        with st.expander("⚡ Quick Add Ticker"):
            quick_ticker = st.text_input("Ticker Symbol", placeholder="AAPL")
            if st.button("Add"):
                success, msg = add_ticker_to_watchlist(quick_ticker.upper(), st.session_state['user'].id)
                if success or "Already" in msg:
                    with st.spinner("Fetching data..."):
                        backfill_new_stock(quick_ticker.upper())
                    st.session_state['page'] = "Dashboard"
                    st.rerun()
                else:
                    st.error(msg)
        
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.session_state['user'] = None
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
                        # Use existing add logic
                        success, msg = add_ticker_to_watchlist(stock['symbol'], st.session_state['user'].id)
                        
                        if success or "Already" in msg:
                            st.toast(f"✅ {stock['symbol']} added! Fetching history...")
                            
                            # Trigger Backfill
                            with st.spinner("⏳ Downloading data..."):
                                backfill_new_stock(stock['symbol'])
                            
                            # Redirect to Dashboard
                            st.session_state['page'] = "Dashboard"
                            st.session_state['selected_ticker'] = None
                            st.rerun()
                        else:
                            st.error(msg)
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
            color = "normal" if idx['Change'] >= 0 else "inverse"
            cols[i].metric(label=idx['Index'], value=f"{idx['Price']:,.0f}", delta=f"{idx['Change']:.2f}%", delta_color=color)
    st.markdown("---")

    # 1. FILTER DATA FOR CURRENT USER
    user_id = st.session_state['user'].id
    my_tickers = get_user_watchlist(user_id)
    all_data = get_portfolio_summary()
    
    # Filter: Keep only rows where the ticker is in MY watchlist
    my_portfolio = [item for item in all_data if item['ticker'] in my_tickers]

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
                
                # ... inside the loop ...
                with col:
                    # Color Scheme
                    sentiment_color = "normal"
                    if stock['sentiment'] == 'positive': sentiment_color = "off"
                    elif stock['sentiment'] == 'negative': sentiment_color = "inverse"
                
                    # --- 🔥 NEW: Dynamic Currency Logic ---
                    currency_symbol = "$" # Default
                    if ".NS" in stock['ticker'] or ".BO" in stock['ticker']:
                        currency_symbol = "₹"

                    # Render Card
                    with st.container(border=True):
                        st.metric(
                        label=stock['ticker'],
                        value=f"{currency_symbol}{stock['price']:,.2f}", # <--- Use variable here
                        delta=f"{stock['sentiment'].upper()} ({stock['confidence']:.2f})",
                        delta_color=sentiment_color
                    )
                        
                        if st.button(f"🔍 Deep Dive", key=f"btn_{stock['ticker']}"):
                            st.session_state.selected_ticker = stock['ticker']
                            st.rerun()

    # CONDITION B: SHOW THE DEEP DIVE (If a ticker IS selected)
    else:
        selected_ticker = st.session_state.selected_ticker
        
        if st.button("⬅️ Back to Dashboard"):
            st.session_state.selected_ticker = None
            st.rerun()
            
        st.markdown(f"## 🔎 Deep Dive Analysis: {selected_ticker}")
        
        # --- 1. FETCH & ENRICH DATA ---
        stock_data = fetch_unified_data(selected_ticker)
        
        if stock_data.empty:
            st.error("No data found. Please run 'backfill_manager.py' first.")
        else:
            # Calculate Technical Indicators
            stock_data = calculate_technical_indicators(stock_data)
            latest_tech_row = stock_data.iloc[-1]
            tech_signal = get_market_signal(latest_tech_row)

            # --- 2. PREDICTION MODULE ---
            predicted_price, ai_signal = predict_next_day_price(selected_ticker, stock_data)

            # --- 3. GENERATIVE AI BRIEFING ---
            latest = get_latest_data(selected_ticker)
            if latest:
                with st.spinner(f"🤖 AI Analyst is reading the news for {selected_ticker}..."):
                    ai_context = {
                        'price': latest['price'],
                        'rsi': latest_tech_row['RSI'],
                        'sentiment': latest['sentiment'],
                        'headline': latest['headline'],
                        'prediction': ai_signal if predicted_price else "Wait & See"
                    }
                    briefing = generate_market_briefing(selected_ticker, ai_context)

                st.markdown(f"""
                    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 5px solid #00E676; margin-bottom: 20px;">
                    <h4 style="margin-top:0; color: #00E676;">🤖 AI Analyst Verdict</h4>
                    <p style="font-size: 1.1em; line-height: 1.6;">{briefing}</p>
                    </div>
                    """, unsafe_allow_html=True)

            # --- 4. METRICS ROW ---
            # ... inside the Deep Dive section ...

            # --- 4. METRICS ROW ---
            c1, c2, c3, c4 = st.columns(4)
            
            # --- 🔥 NEW: Dynamic Currency Logic ---
            currency_symbol = "$"
            if ".NS" in selected_ticker or ".BO" in selected_ticker:
                currency_symbol = "₹"

            c1.metric("Current Price", f"{currency_symbol}{latest['price']:,.2f}") # <--- Use variable here
            
            sent_color = "normal"
            if latest['sentiment'] == 'positive': sent_color = "off"
            elif latest['sentiment'] == 'negative': sent_color = "inverse"
            c2.metric("News Sentiment", latest['sentiment'].upper(), f"{latest['confidence']:.2f} conf", delta_color=sent_color)
            
            c3.metric("Technical Signal", "RSI: " + f"{latest_tech_row['RSI']:.0f}", tech_signal)
            
            if predicted_price:
                c4.metric("AI Forecast (24h)", f"${predicted_price:,.2f}", ai_signal)
            else:
                c4.metric("AI Forecast", "Calculating...", "Need Data", delta_color="off")

            # --- 5. THE PRO CHART (Price + SMA + RSI) ---
            st.subheader(f"📉 Advanced Market Analysis")
            
            from plotly.subplots import make_subplots
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
                              legend=dict(orientation="h", y=1.02))
            st.plotly_chart(fig, use_container_width=True)
            
            # --- 6. DATA TABLE ---
            st.dataframe(stock_data.sort_values(by='timestamp', ascending=False))