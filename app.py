import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. PAGE CONFIG
st.set_page_config(page_title="Market Intelligence", layout="wide")
st.title("🤖 AI-Powered Market Sentinel")

# 2. LOAD DATA FROM DB
def load_data():
    conn = sqlite3.connect("finance.db")
    # Get all data sorted by time
    df = pd.read_sql("SELECT * FROM market_log ORDER BY timestamp ASC", conn)
    conn.close()
    return df

df = load_data()

# 3. SIDEBAR: Select Stock
if not df.empty:
    # Get unique list of tickers
    ticker_list = df['ticker'].unique().tolist()
    selected_ticker = st.sidebar.selectbox("Select Asset", ticker_list)

    # Filter data for that ticker
    stock_data = df[df['ticker'] == selected_ticker]
    
    # 4. METRICS (Top Row)
    # Get the very latest record
    latest_record = stock_data.iloc[-1]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Latest Price", f"{latest_record['price']:.2f}")
    col2.metric("AI Sentiment", latest_record['sentiment'].upper(), 
                delta=f"{latest_record['confidence']:.2f} conf")
    col3.write(f"**Latest Headline:**\n_{latest_record['headline']}_")

    # 5. VISUALIZATION (Price vs Sentiment)
    st.subheader(f"📉 {selected_ticker} Performance Analysis")
    
    # Create a chart with 2 Y-axes (Price on left, Sentiment on right)
    fig = go.Figure()

    # Line 1: Stock Price
    fig.add_trace(go.Scatter(
        x=stock_data['timestamp'], 
        y=stock_data['price'],
        name="Stock Price",
        line=dict(color='blue', width=2)
    ))

    # Line 2: Sentiment Score (We map 'positive' to 1, 'negative' to -1)
    # Helper to convert text to number for plotting
    def sentiment_to_score(row):
        if row['sentiment'] == 'positive': return row['confidence']
        if row['sentiment'] == 'negative': return -row['confidence']
        return 0
    
    stock_data['sentiment_score'] = stock_data.apply(sentiment_to_score, axis=1)

    fig.add_trace(go.Bar(
        x=stock_data['timestamp'], 
        y=stock_data['sentiment_score'],
        name="Sentiment Strength",
        yaxis="y2",
        marker_color=stock_data['sentiment_score'].apply(lambda x: 'green' if x > 0 else 'red'),
        opacity=0.3
    ))

    # Layout for Double Axis
    fig.update_layout(
        yaxis=dict(title="Price"),
        yaxis2=dict(title="Sentiment Score (-1 to +1)", overlaying="y", side="right"),
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)
    
    # Show Raw Data Table
    st.caption("Raw Data Log")
    st.dataframe(stock_data[['timestamp', 'price', 'sentiment', 'confidence', 'headline']].sort_values(by='timestamp', ascending=False))

else:
    st.warning("⚠️ Database is empty. Run 'main.py' to fetch data first.")

# 6. REFRESH BUTTON
if st.sidebar.button("🔄 Refresh Data"):
    st.rerun()