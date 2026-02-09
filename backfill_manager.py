import os
import time
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

# --- CONFIGURATION ---
START_DATE = "2020-01-01"  # Force a fixed start date
CHUNK_SIZE = 1000

# 1. SETUP & AUTH
load_dotenv()
URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_KEY")  # ⚠️ Use SERVICE_ROLE key

if not URL or not KEY:
    raise ValueError("❌ Credentials missing. Check .env file.")

supabase = create_client(URL, KEY)

def get_unique_tickers():
    print("🔍 Scanning Watchlist...")
    try:
        response = supabase.table('market_log').select('ticker').execute()
        data = response.data
        if data:
            return list(set([item['ticker'] for item in data]))
        return []
    except Exception as e:
        print(f"⚠️ Error fetching tickers: {e}")
        return []

def backfill_ticker(ticker):
    # Dynamic End Date = Tomorrow (to ensure we capture today's close in all timezones)
    end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"\n⏳ Downloading history for: {ticker} ({START_DATE} to {end_date})...")
    
    try:
        # 1. Fetch Data with EXPLICIT DATES
        df = yf.download(ticker, start=START_DATE, end=end_date, interval="1d", progress=False)
        
        if df.empty:
            print(f"❌ No data found for {ticker}.")
            return
        
        # Flatten Multi-Index if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.reset_index(inplace=True)
        
        # 2. Format Data
        records = []
        for _, row in df.iterrows():
            date_val = row.get('Date') if 'Date' in row else row.get('Datetime')
            
            if pd.isna(date_val): continue
                
            clean_record = {
                "ticker": ticker,
                "timestamp": pd.to_datetime(date_val).isoformat(),
                "open": round(float(row['Open']), 2),
                "high": round(float(row['High']), 2),
                "low": round(float(row['Low']), 2),
                "close": round(float(row['Close']), 2),
                "volume": int(row['Volume'])
            }
            records.append(clean_record)
        
        # 3. DELETE OLD DATA (The Clean Slate Fix)
        print(f"   🧹 Clearing old {ticker} history from DB...")
        supabase.table('price_history').delete().eq('ticker', ticker).execute()
        
        # 4. UPLOAD NEW DATA
        print(f"   ✅ Formatted {len(records)} rows. Uploading fresh history...")

        total_uploaded = 0
        for i in range(0, len(records), CHUNK_SIZE):
            chunk = records[i : i + CHUNK_SIZE]
            try:
                supabase.table('price_history').insert(chunk).execute()
                total_uploaded += len(chunk)
                print(f"      🔹 Batch {i//CHUNK_SIZE + 1} uploaded...")
                time.sleep(0.1) 
            except Exception as e:
                print(f"      ❌ Batch Error: {e}")

        print(f"🎉 {ticker}: Fully Synced ({total_uploaded} records).")

    except Exception as e:
        print(f"❌ Critical Error for {ticker}: {e}")

def run_backfill_pipeline():
    print("🚀 STARTING GAP-FILL OPERATION...")
    tickers = get_unique_tickers()
    
    if not tickers:
        print("❌ No tickers found.")
        return

    print(f"📋 Target Watchlist: {tickers}")
    
    for ticker in tickers:
        backfill_ticker(ticker)

    print("\n✅ GAP FILL COMPLETE. The 'Missing Year' is gone.")

if __name__ == "__main__":
    run_backfill_pipeline()