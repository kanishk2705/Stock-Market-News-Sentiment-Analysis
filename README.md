# 📂 Market Sentiment Intelligence System

**Project Duration:** Jan 2026 – Present  
**Built By:** A C KANISHK  

---

## 📖 The Evolution Story

### 🔹 Phase 1: The Ingestion Layer (The "Body")

**Goal:**  
Stop reading financial news manually by automating data collection.

**Challenges:**  
- Financial data is scattered across multiple sources  
- Yahoo Finance API structure is unstable due to deeply nested JSON responses  

**Solution:**  
- Developed a Python ETL script (`fetch_data.py`) using **yfinance**  
- Implemented custom parsing logic to handle dynamic JSON schemas  
- Normalized currency symbols (₹ vs $) across Indian and US markets  

**Result:**  
- Generated a console-based report displaying live stock prices and headlines for a **hardcoded portfolio**

---

### 🔹 Phase 2: The Cognitive Layer (The "Brain")

**Goal:**  
Convert financial text into quantitative insights.

**Challenges:**  
- Generic sentiment models fail in financial contexts  
  - Example: *“Cost cutting”* is negative in general English but positive for stock performance  

**Solution:**  
- Integrated **FinBERT**, a Transformer model pre-trained on financial text  
- Built a microservice (`sentiment_engine.py`) to score headlines using confidence vectors  

**Result:**  
- Successfully identified *bearish sentiment* from a “Trade War” headline for **NVIDIA**, even before price movement occurred  

---

### 🔹 Phase 3: The Persistence Layer (The "Memory")

**Goal:**  
Eliminate data loss and enable historical analysis.

**Challenges:**  
- Script-based execution leads to loss of historical data after runtime  

**Solution:**  
- Designed and implemented a structured **SQL database schema**  
- **Evolution:** Started with **SQLite** for rapid prototyping and testing  

---

### 🔹 Phase 4: The Interface (The "Face")

**Goal:**  
Make the system usable for non-technical users.

**Challenges:**  
- Terminal-based logs are difficult to interpret  

**Solution:**  
- Developed a **Streamlit dashboard** (`app.py`)  

**Features:**  
- Interactive visualizations using **Plotly**  
- Dual-axis graphs showing **Stock Price vs. Sentiment Correlation**

---

## ⚠️ Drawbacks

1. **Hardcoded Portfolio**  
   - The system currently supports only a static portfolio, whereas real-world users expect personalized portfolios.

2. **Manual Database Updates**  
   - Database maintenance requires manual intervention, reducing scalability and automation.

3. **No Email Alert System**  
   - Lacks automated email notifications for critical market events or sentiment changes.

4. **Limited Sentiment Scope**  
   - Market sentiment is inferred only from the latest headline, which may lead to unreliable conclusions.

5. **Local Database Usage**  
   - Reliance on SQLite limits concurrent access and production-level scalability.

6. **No Future Prediction Capability**  
   - The system focuses on analysis and does not include predictive or forecasting models.

---

## 🚀 Future Enhancements (Planned)

- User-specific dynamic portfolios  
- Automated ETL scheduling  
- Email and push notification system  
- Aggregated multi-headline sentiment analysis  
- Migration to cloud-based databases (PostgreSQL)  
- Time-series forecasting and predictive modeling  

---
