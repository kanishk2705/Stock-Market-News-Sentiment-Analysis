# 🤖 Market Sentinel: AI-Powered Financial SaaS (V2.0)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Supabase](https://img.shields.io/badge/Backend-Supabase_&_RLS-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)
![Llama 3](https://img.shields.io/badge/GenAI-Llama_3.3_(Groq)-orange?style=for-the-badge&logo=openai&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)

**Project Status:** 🟢 Active (V2.0 Enterprise)  
**Architect:** A C KANISHK

> **A Multi-User Financial Intelligence Platform.**
>
> **Market Sentinel** is not just a dashboard; it is a **Full-Stack SaaS** that autonomously tracks global assets, secures user data with Row-Level Security (RLS), and employs **Generative AI** to write professional "Wall Street-style" briefings for every stock in your portfolio.

---

## 📖 The Engineering Evolution (V1 ➡️ V2)

### 🔹 Phase 1: The Ingestion Layer (The "Body")
**Goal:** Automate the chaotic process of financial data collection.
* **The Upgrade:** Moved beyond simple scraping. The system now features **"Auto-Onboarding"**: adding a new ticker (e.g., `NVDA`) triggers an immediate **2-year historical backfill** via `yfinance`, normalizing multi-currency data (₹/$) instantly.

### 🔹 Phase 2: The SaaS Architecture (The "Fortress") 🆕
**Goal:** Transform a single-user tool into a secure, multi-tenant platform.
* **Challenge:** How to let multiple users track different stocks without seeing each other's data?
* **Solution:** Implemented **Supabase Authentication** with **Row Level Security (RLS)**.
* **Impact:** The database acts as a firewall. User A cannot query User B’s watchlist, even if they try via API.

### 🔹 Phase 3: The Generative AI Analyst (The "Brain") 🆕
**Goal:** Move from "Numbers" (RSI: 70) to "Meaning" ("The stock is overbought due to...").
* **Solution:** Integrated **Llama 3.3 (70B)** via the **Groq LPU Engine** for sub-second inference.
* **Feature:** The "Deep Dive" engine feeds technical indicators + news headlines into the LLM, which generates a concise, professional executive summary explaining *why* the market is moving.

### 🔹 Phase 4: The Global Search Engine (The "Eyes") 🆕
**Goal:** Allow users to find any stock, not just US tech giants.
* **Solution:** Reverse-engineered the **Yahoo Finance Type-Ahead API** to build a "Global Search" page.
* **Impact:** Users can now search for over **100,000+ assets** across exchanges (NSE, BSE, NYSE, NASDAQ) and add them instantly.

### 🔹 Phase 5: The Self-Healing Automaton (The "Heartbeat")
**Goal:** Zero human maintenance.
* **Solution:** A "Cloud Robot" (GitHub Actions) wakes up nightly to fetch fresh data.
* **Resilience:** If data is missing (e.g., a holiday or API failure), the system detects the gap, logs the error, and attempts a self-correction or "force fetch" on the next run.

---

## 🛠️ Tech Stack & Architecture

| Layer | Technology | Role |
| :--- | :--- | :--- |
| **Frontend** | Streamlit | Responsive "Bloomberg Terminal" UI with Sidebar Nav |
| **Backend** | Python 3.10 | Core business logic and data processing |
| **Auth & DB** | Supabase (PostgreSQL) | Auth, Database, and Row Level Security (RLS) policies |
| **Generative AI** | Groq API (Llama 3.3) | Generating natural language market briefings |
| **Data Feed** | yfinance / Yahoo API | Real-time price, history, and global ticker search |
| **DevOps** | GitHub Actions | Scheduled Cron Jobs for automated data pipelines |
| **Visualization** | Plotly | Interactive, multi-layer financial charting |

---

## 📸 Key Features

1.  **🔐 Secure Login:** Email/Password authentication with persistent sessions.
2.  **🌍 Global Search:** Find stocks from India (NSE/BSE) to the US (NYSE) with auto-currency detection (₹/$).
3.  **🤖 AI Verdict:** A "Smart Card" at the top of every analysis page tells you *exactly* what is happening in plain English.
4.  **📉 Technical Deep Dive:** Interactive charts overlaying SMA-50, SMA-200, and RSI indicators.
5.  **⚡ Instant Refresh:** Sidebar controls allow users to force-fetch the latest live data.

---

## 🚀 Future Roadmap (V3.0)

We are constantly pushing the boundaries of what this platform can do.

- [ ] **Advanced Forecasting:** Upgrade the prediction engine from Random Forest to **LSTM (Long Short-Term Memory)** Neural Networks for capturing non-linear market patterns.
- [ ] **Social Sentiment:** Expand the NLP engine to analyze **Reddit (r/wallstreetbets) and Twitter (X)** sentiment, not just news.
- [ ] **Portfolio Optimization:** Add a module to suggest "Rebalancing" based on Sharpe Ratio calculations.

---

## ⚙️ How to Run Locally

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/kanishk2705/Stock-Market-News-Sentiment-Analysis.git](https://github.com/kanishk2705/Stock-Market-News-Sentiment-Analysis.git)
    cd Stock-Market-News-Sentiment-Analysis
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Secrets**
    Create a `.env` file in the root directory. You will need keys for the Database and the AI Engine.
    ```ini
    # Database & Auth
    SUPABASE_URL="[https://your-project.supabase.co](https://your-project.supabase.co)"
    SUPABASE_KEY="your-anon-key"
    
    # AI Engine
    GROQ_API_KEY="gsk_..."
    
    # (Optional) For Admin Alerts
    EMAIL_SENDER="your-email@gmail.com"
    EMAIL_PASSWORD="your-app-password"
    ```

4.  **Launch the Platform**
    ```bash
    streamlit run app.py
    ```

---

> *"The goal is not just to see the data, but to understand the story behind it."* — **Market Sentinel V2**