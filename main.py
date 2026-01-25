import pandas as pd
from fetch_data import fetch_portfolio_data
from sentiment_engine import analyze_headline
from database import init_db, save_log  # <-- IMPORTED DB TOOLS

def run_market_intelligence():
    print("🚀 STARTING MARKET INTELLIGENCE SYSTEM...\n")
    
    # 0. ENSURE DB EXISTS
    init_db()

    # 1. FETCH RAW DATA
    print("--- 📡 PHASE 1: INGESTING LIVE DATA ---")
    raw_data = fetch_portfolio_data()
    print(f"✅ Ingestion Complete. Fetched {len(raw_data)} assets.\n")

    # 2. APPLY AI SENTIMENT ANALYSIS
    print("--- 🧠 PHASE 2: RUNNING SENTIMENT INTELLIGENCE ---")
    enriched_data = []

    for item in raw_data:
        ticker = item['Ticker']
        headline = item['Headline']
        
        if headline != "N/A" and headline != "Format Unknown":
            sentiment = analyze_headline(headline)
            label = sentiment['label']
            score = sentiment['score']
        else:
            label = "neutral"
            score = 0.0

        item['Sentiment'] = label
        item['Confidence'] = score
        enriched_data.append(item)
        
        print(f"🤖 Analyzed {ticker}: {label.upper()} ({score:.2f})")

    # 3. SAVE TO DATABASE (PHASE 3)
    print("\n--- 💾 PHASE 3: DATA PERSISTENCE ---")
    save_log(enriched_data)

    # 4. DISPLAY SUMMARY
    print("\n--- 📊 FINAL MARKET REPORT ---")
    df = pd.DataFrame(enriched_data)
    if not df.empty:
        df['Signal'] = df.apply(lambda x: "🟢 BULLISH" if x['Sentiment'] == 'positive' and x['Confidence'] > 0.8 else ("🔴 BEARISH" if x['Sentiment'] == 'negative' else "⚪ NEUTRAL"), axis=1)
        print(df[['Ticker', 'Price', 'Signal', 'Sentiment']].to_string(index=False))

if __name__ == "__main__":
    run_market_intelligence()