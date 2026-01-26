# 🤖 Market Sentiment Intelligence System

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)
![FinBERT](https://img.shields.io/badge/AI-FinBERT-yellow?style=for-the-badge)

**Project Duration:** Jan 2026 – Present  
**Built By:** A C KANISHK  

> **A Cloud-Native Financial Intelligence Platform that quantifies market sentiment using NLP and visualizes its impact on stock prices in real-time.**

---

## 📖 The Engineering Evolution

### 🔹 Phase 1: The Ingestion Layer (The "Body")
**Goal:** Stop reading financial news manually by automating data collection.
* **Challenge:** Financial data is scattered; APIs like Yahoo Finance have unstable, deep JSON structures.
* **Solution:** Built a robust ETL script (`fetch_data.py`) with custom parsing logic to normalize multi-currency assets (₹ for NSE, $ for NYSE) dynamically.
* **Current State:** The system now fetches data **dynamically** based on user watchlists, moving away from hardcoded portfolios.

### 🔹 Phase 2: The Cognitive Layer (The "Brain")
**Goal:** Convert financial text into quantitative insights.
* **Challenge:** Generic sentiment models fail in finance (e.g., *"Cost cutting"* is positive for stocks but negative in general English).
* **Solution:** Integrated **FinBERT**, a Transformer model pre-trained on financial texts.
* **Result:** The system calculates a "Confidence Score" (0-1) for every headline to distinguish between weak rumors and strong market signals.

### 🔹 Phase 3: The Persistence Layer (The "Memory")
**Goal:** Eliminate data loss and enable historical analysis.
* **Challenge:** Local scripts lose data when stopped. SQLite locks files during concurrent writes.
* **Solution:** Migrated from a local file-based DB to a **Hosted Cloud Database (PostgreSQL via Supabase)**.
* **Impact:** Supports concurrent users and keeps data safe 24/7, independent of the application state.

### 🔹 Phase 4: The Interface (The "Face")
**Goal:** Make the system usable for non-technical users.
* **Solution:** Developed an interactive **Streamlit Dashboard** (`app.py`).
* **New Features:**
    * **User Profiles:** Dynamic login to manage personal watchlists.
    * **Real-time Charts:** Dual-axis plotting of Stock Price vs. Sentiment Intensity using **Plotly**.
    * **Cloud Connectivity:** Direct connection to the Supabase backend.

---

## 🛠️ Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Language** | Python 3.10 | Core logic and scripting |
| **Frontend** | Streamlit | Interactive web dashboard |
| **Database** | PostgreSQL (Supabase) | Cloud-hosted relational database |
| **AI Model** | FinBERT (Hugging Face) | Financial Sentiment Analysis (NLP) |
| **Data Source** | yfinance | Real-time market data API |
| **Visualization** | Plotly | Interactive financial charting |

---

## ⚠️ Current Limitations (To Be Addressed)

Although the system has moved to the Cloud, the following areas are under active development:

1.  **Manual Triggering:** * The "Robot" (`main.py`) still requires manual execution to fetch daily data. (Automation via GitHub Actions is the next milestone).
2.  **No "Push" Alerts:** * Users must visit the dashboard to see risks; the system does not yet send emails/SMS for critical sentiment drops.
3.  **Snapshot Analysis:** * Currently analyzes the *latest* headline. Planned upgrade to "Batch Analysis" (Top 5 headlines) for better accuracy.
4.  **No Predictive Modeling:** * The system analyzes the *present* but does not yet forecast *future* prices using regression/LSTM.

---

## 🚀 Roadmap & Future Enhancements

- [x] **Dynamic Portfolios** (Users can add/remove stocks) ✅ *Completed*
- [x] **Cloud Database Migration** (SQLite → PostgreSQL) ✅ *Completed*
- [ ] **Automated Cron Jobs:** Deploying GitHub Actions for 24/7 autonomous data fetching.
- [ ] **Predictive Engine:** Implementing Linear Regression/LSTM to forecast next-day prices.
- [ ] **Alert System:** Email notifications for high-confidence bearish signals.

---

## ⚙️ How to Run Locally

1.  **Clone the Repo**
    ```bash
    git clone [https://github.com/kanishk2705/Stock-Market-News-Sentiment-Analysis.git](https://github.com/kanishk2705/Stock-Market-News-Sentiment-Analysis.git)
    cd market-sentinel
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Secrets**
    Create a `.env` file in the root directory:
    ```ini
    DATABASE_URL="postgresql://postgres.[USER]:[PASSWORD]@[aws-0-ap-south-1.pooler.supabase.com:6543/postgres](https://aws-0-ap-south-1.pooler.supabase.com:6543/postgres)"
    ```

4.  **Initialize Database**
    ```bash
    python database.py
    ```

5.  **Run the Dashboard**
    ```bash
    streamlit run app.py
    ```

---