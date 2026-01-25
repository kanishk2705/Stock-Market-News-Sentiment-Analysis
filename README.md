# 📂 Market Sentiment Intelligence System
# Project Duration: Jan 2026 - Present
# Built By: A C KANISHK

# 📖 The Evolution Story

# Phase 1: The Ingestion Layer (The "Body")

Goal: Stop reading news manually. Build a system to fetch it for me.

•	Challenge: Financial data is scattered. Yahoo Finance API structure is unstable (nested JSONs).
•	Solution: Built a Python ETL script (fetch_data.py) using yfinance. Implemented custom logic to parse dynamic JSON schemas and normalize currency symbols (₹ vs $) across Indian and US markets.
•	Result: A console report showing live prices and headlines for a hardcoded portfolio.

# Phase 2: The Cognitive Layer (The "Brain")

Goal: Turn text into math.

•	Challenge: Standard sentiment models fail in finance (e.g., "Cost cutting" is good for stocks, but bad in general English).
•	Solution: Integrated FinBERT, a Transformer model pre-trained on financial texts. Built a microservice (sentiment_engine.py) that scores headlines with a confidence vector.
•	Result: The system could correctly identify that a "Trade War" headline was BEARISH for Nvidia, even if the price hadn't moved yet.

# Phase 3: The Persistence Layer (The "Memory")

Goal: Solve "Data Amnesia."

•	Challenge: Scripts forget data when they stop. We needed historical context.
•	Solution: Architected a SQL database schema.
o	Evolution: Started with local SQLite for rapid prototyping.

# Phase 4: The Interface (The "Face")

Goal: Make it usable for non-engineers.

•	Challenge: Terminal logs are hard to read.
•	Solution: Built a Streamlit Dashboard (app.py).
o	Features: Interactive Charts (Plotly).
o	Tech: Dual-Axis graphing to visualize Price vs. Sentiment correlation.

# Drawbacks:

1. Hardcoded Portfolio: The system supports only a static portfolio, whereas real-world users expect personalized portfolios.
2. Manual Database Updates: The database requires frequent manual updates, making maintenance inefficient.
3. No Email Alert System: There is no automated email notification mechanism to alert users about important market events.
4. Limited Sentiment Analysis: Market sentiment is derived only from the latest headline, which can lead to unreliable or risky conclusions.
5. Local Database Usage: The application relies on a local SQLite database, limiting scalability and concurrent access.
6. No Future Prediction Capability: The system does not provide any predictive insights or future market trend forecasting.