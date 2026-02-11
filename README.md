# 🤖 Market Sentiment Intelligence System (V1.0)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)
![FinBERT](https://img.shields.io/badge/AI-FinBERT-yellow?style=for-the-badge)
![GitHub Actions](https://img.shields.io/badge/Automation-GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)

**Project Duration:** Jan 2026 – Present  
**Built By:** A C KANISHK  

> **A Cloud-Native Financial Intelligence Platform that quantifies market sentiment using NLP, forecasts future price trends, and autonomously alerts users of critical risks.**

---

## 📖 The Engineering Evolution

### 🔹 Phase 1: The Ingestion Layer (The "Body")
**Goal:** Stop reading financial news manually by automating data collection.
* **Challenge:** Financial data is scattered; APIs like Yahoo Finance have unstable, deep JSON structures.
* **Solution:** Built a robust ETL script (`fetch_data.py`) with custom parsing logic to normalize multi-currency assets (₹ for NSE, $ for NYSE) dynamically.

### 🔹 Phase 2: The Cognitive Layer (The "Brain")
**Goal:** Convert financial text into quantitative insights.
* **Challenge:** Generic sentiment models fail in finance (e.g., *"Cost cutting"* is positive for stocks but negative in general English).
* **Solution:** Integrated **FinBERT**, a Transformer model pre-trained on financial texts.
* **Result:** The system calculates a "Confidence Score" (0-1) for every headline to distinguish between weak rumors and strong market signals.

### 🔹 Phase 3: The Persistence Layer (The "Memory")
**Goal:** Eliminate data loss and enable historical analysis.
* **Challenge:** Local scripts lose data when stopped. SQLite locks files during concurrent writes.
* **Solution:** Migrated to a **Hosted Cloud Database (PostgreSQL via Supabase)**.
* **Impact:** Supports concurrent users and keeps data safe 24/7.

### 🔹 Phase 4: The Interface (The "Face")
**Goal:** Make the system usable for non-technical users.
* **Solution:** Developed an interactive **Streamlit Dashboard** (`app.py`).
* **Features:** Dynamic User Profiles, Dual-Axis Plotly Charts (Price vs. Sentiment), and Real-Time Cloud Sync.

### 🔹 Phase 5: The Automation Layer (The "Heartbeat") ✅
**Goal:** Remove the human bottleneck.
* **Challenge:** The script only worked when I manually ran it.
* **Solution:** Deployed a **"Cloud Robot"** using **GitHub Actions**.
* **Impact:** The system now wakes up automatically every night (UTC), fetches global market data, runs the AI analysis, saves to the cloud, and shuts down—without zero human intervention.

### 🔹 Phase 6: The Predictive Engine (The "Oracle") ✅
**Goal:** Answer the question: *"Where is the price going tomorrow?"*
* **Solution:** Implemented a **Linear Regression** model (`prediction_engine.py`) using `scikit-learn`.
* **Logic:** It analyzes the correlation between "Time" and "Accumulated Sentiment" to forecast the next day's closing price.
* **Status:** Operational (Requires >5 days of data to generate valid signals).

### 🔹 Phase 7: The Alerting System (The "Voice") ✅
**Goal:** Notify the user of critical risks without them checking the dashboard.
* **Solution:** Built an SMTP-based **Email Notification Service** (`alert_system.py`).
* **Logic:** The system filters for "High Confidence Negative Signals" (Sentiment=Negative AND Confidence > 0.8) and instantly emails a "Crisis Report" to the administrator.

---

## 🛠️ Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Language** | Python 3.10 | Core logic and scripting |
| **Frontend** | Streamlit | Interactive web dashboard |
| **Database** | PostgreSQL (Supabase) | Cloud-hosted relational database |
| **AI Model** | FinBERT (Hugging Face) | Financial Sentiment Analysis (NLP) |
| **Forecasting** | Scikit-Learn | Linear Regression for Price Prediction |
| **Automation** | GitHub Actions | CI/CD & Scheduled Cron Jobs |
| **Alerts** | SMTP / Gmail API | Automated Risk Notifications |

---

## ⚠️ Current Limitations (V1.0)

While the Core V1 system is complete, the following areas are targeted for V2:

1.  **Linear Model Simplicity:** The current prediction engine uses Linear Regression, which is fast but misses complex non-linear market patterns. (Planned Upgrade: **LSTM/RNN**).
2.  **Single-Tenant Alerts:** The alert system currently emails the admin only. It does not yet support multi-user routing.
3.  **Cold Start:** The predictive engine requires at least 5 days of continuous data collection before it begins generating forecasts.
4.  **No Historical Backfill:** The system only knows data from the day it was activated; it does not yet fetch the last 5 years of history.

---

## 🚀 Roadmap (V2.0 - The "Platform" Upgrade)

- [x] **Bloomberg-Style Dashboard:** Upgrade UI to a "Card Grid" layout with live Market Indices (Nifty, Nasdaq).
- [x] **Historical Backfill:** Feature to fetch 5 years of past data for immediate deep learning training.
- [x] **Deep Learning Engine:** Replacing Linear Regression with **Random Forest Regressor** and will update to **LSTM networks** in the near future.
- [ ] **SaaS Architecture:** Implementing Multi-User Authentication and Row Level Security (RLS).
- [ ] **Generative AI Analyst:** Integrating LLMs (Llama/GPT) to write text summaries of *why* a stock is moving.

---

## ⚙️ How to Run Locally

1.  **Clone the Repo**
    ```bash
    git clone [https://github.com/kanishk2705/Stock-Market-News-Sentiment-Analysis.git](https://github.com/kanishk2705/Stock-Market-News-Sentiment-Analysis.git)
    cd Stock-Market-News-Sentiment-Analysis
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Secrets**
    Create a `.env` file in the root directory:
    ```ini
    DATABASE_URL="postgresql://postgres.[USER]:[PASSWORD]@[aws-0-ap-south-1.pooler.supabase.com:6543/postgres](https://aws-0-ap-south-1.pooler.supabase.com:6543/postgres)"
    EMAIL_SENDER="your-email@gmail.com"
    EMAIL_PASSWORD="your-app-password"
    SUPABASE_URL="your-project-url"
    SUPABASE_KEY="your-secret-key"
    ```

4.  **Run the Dashboard**
    ```bash
    streamlit run app.py
    ```

---