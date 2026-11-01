import pandas as pd
from fetch_data import fetch_portfolio_data
from sentiment_engine import analyze_headline
from database import init_db, save_log, backfill_new_stock, reset_demo_account
from alert_system import send_market_alert
from datetime import datetime, timezone

def run_market_intelligence():
    print("🚀 STARTING MARKET INTELLIGENCE SYSTEM (CLOUD EDITION)...\n")
    
    # 1. INITIALIZE CLOUD DB
    init_db()
    try:
        ok, msg = reset_demo_account()
        print(f"{'✅' if ok else 'ℹ️'} {msg}")
    except Exception as e:  # the demo account must never block the scan
        print(f"⚠️ Demo account reset failed: {e}")

    # 2. FETCH RAW DATA
    # This will now look at your Supabase 'watchlist' table
    print("--- 📡 PHASE 1: INGESTING LIVE DATA ---")
    raw_data = fetch_portfolio_data()
    
    if not raw_data:
        print("❌ Process Aborted: Watchlist is empty.")
        return

    print(f"✅ Ingestion Complete. Fetched {len(raw_data)} assets.\n")

    # 3. APPLY AI SENTIMENT ANALYSIS
    print("--- 🧠 PHASE 2: RUNNING SENTIMENT INTELLIGENCE ---")
    enriched_data = []

    for item in raw_data:
        ticker = item.get('Ticker') # Use .get() to be safe
        headline = item.get('Headline')
        
        # Analyze Sentiment
        if headline and headline != "N/A" and headline != "Format Unknown":
            sentiment = analyze_headline(headline)
            label = sentiment['label']
            score = sentiment['score']
        else:
            label = "neutral"
            score = 0.0

        print(f"🤖 Analyzed {ticker}: {label.upper()} ({score:.2f})")

        # --- CRITICAL FIX START ---
        # Create a new, clean dictionary with LOWERCASE keys for the database
        clean_record = {
            "ticker": ticker,
            "headline": headline,
            "price": item.get('Price', 0), # Ensure Price exists
            "sentiment": label,
            "confidence": score,
            # Always UTC so local runs and GitHub Actions runs sort consistently
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }
        enriched_data.append(clean_record)
        # --- CRITICAL FIX END ---

    # 4. SAVE TO CLOUD DATABASE
    print("\n--- 💾 PHASE 3: CLOUD PERSISTENCE ---")
    save_log(enriched_data)

    # 5. SELF-HEALING: top up any missing days of daily price history
    print("\n--- 🩹 PHASE 4: PRICE HISTORY GAP-FILL ---")
    for record in enriched_data:
        ok, msg = backfill_new_stock(record['ticker'])
        print(f"{'✅' if ok else '❌'} {record['ticker']}: {msg}")

    # 6. ALERTING SYSTEM
    print("\n--- 🔔 PHASE 5: ALERTING SYSTEM ---")
    send_market_alert(enriched_data)

    # 7. DISPLAY SUMMARY
    print("\n--- 📊 FINAL MARKET REPORT ---")
    df = pd.DataFrame(enriched_data)
    
    if not df.empty:
        df['signal'] = df.apply(lambda x: "🟢 BULLISH" if x['sentiment'] == 'positive' and x['confidence'] > 0.8 else ("🔴 BEARISH" if x['sentiment'] == 'negative' else "⚪ NEUTRAL"), axis=1)

        print(df[['ticker', 'price', 'signal', 'sentiment']].to_string(index=False))

if __name__ == "__main__":
    run_market_intelligence()