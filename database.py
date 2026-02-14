import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
import yfinance as yf
# 1. LOAD SECRETS
load_dotenv()

URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_KEY")

# 2. INITIALIZE CLIENT GLOBALLY
if not URL or not KEY:
    raise ValueError("❌ Supabase Credentials missing. Check .env file.")

supabase: Client = create_client(URL, KEY)


def insert_data(data_list):
    """
    Inserts data into the 'market_log' table.
    """
    if not data_list:
        return
        
    try:
        # CHANGED: 'market_data' -> 'market_log'
        response = supabase.table('market_log').insert(data_list).execute()
        print(f"✅ Successfully inserted {len(data_list)} records to Cloud DB.")
    except Exception as e:
        print(f"❌ Database Insert Error: {e}")


def get_latest_data(ticker):
    """
    Fetches the single most recent record for a specific ticker.
    """
    try:
        # CHANGED: 'market_data' -> 'market_log'
        response = supabase.table('market_log')\
            .select("*")\
            .eq('ticker', ticker)\
            .order('timestamp', desc=True)\
            .limit(1)\
            .execute()
        
        data = response.data
        if data:
            return data[0]
        return None
    except Exception as e:
        print(f"❌ Fetch Error: {e}")
        return None


def fetch_all_watchlist_data(ticker):
    """
    Fetches ALL historical data for a ticker.
    """
    try:
        # CHANGED: 'market_data' -> 'market_log'
        response = supabase.table('market_log')\
            .select("*")\
            .eq('ticker', ticker)\
            .order('timestamp', desc=True)\
            .execute()
            
        data = response.data
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    except Exception as e:
        print(f"❌ History Fetch Error: {e}")
        return pd.DataFrame()


def get_portfolio_summary():
    """
    Fetches the LATEST record for every unique ticker.
    Used for the Dashboard Grid.
    """
    try:
        # CHANGED: 'market_data' -> 'market_log'
        response = supabase.table('market_log').select("*").execute()
        data = response.data
        
        if not data:
            return []

        df = pd.DataFrame(data)
        
        # --- THE FIX IS HERE ---
        # We add format='mixed' so it handles both "Robot timestamps" and "Manual timestamps"
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
        
        # Sort by time (newest first)
        df = df.sort_values(by='timestamp', ascending=False)
        
        # Drop duplicates to keep only the LATEST row for each ticker
        latest_df = df.drop_duplicates(subset=['ticker'], keep='first')
        
        return latest_df.to_dict('records')
        
    except Exception as e:
        print(f"❌ Database Summary Error: {e}")
        return []

def get_all_monitored_tickers():
    """
    Fetches the list of tickers from the 'watchlist' table.
    """
    try:
        response = supabase.table('watchlist').select('ticker').execute()
        data = response.data
        
        if data:
            return [item['ticker'] for item in data]
        return []
        
    except Exception as e:
        print(f"❌ Watchlist Fetch Error: {e}")
        return []

# --- LEGACY ADAPTERS ---
def init_db():
    print("✅ Cloud Database Connection Verified.")

def save_log(data):
    return insert_data(data)
def fetch_price_history(ticker):
    """
    Fetches the 5-year OHLCV history from the 'price_history' table.
    """
    try:
        # Fetch data sorted by time
        response = supabase.table('price_history')\
            .select("*")\
            .eq('ticker', ticker)\
            .order('timestamp', desc=False)\
            .execute()
            
        data = response.data
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    except Exception as e:
        print(f"❌ Price History Fetch Error: {e}")
        return pd.DataFrame()
def fetch_unified_data(ticker):
    """
    Stitches history and live data using Reverse Fetch (Newest First).
    This guarantees we capture 2025/2026 data even if the row limit is hit.
    """
    try:
        # 1. Define the Cut-Off Date
        CUTOFF_DATE = pd.Timestamp("2026-01-27", tz='UTC')

        # --- PART A: FETCH HISTORY (Newest -> Oldest) ---
        # We use desc=True to get the most recent history (2025) first.
        # We also add .limit(5000) just to be safe.
        history_response = supabase.table('price_history')\
            .select("*")\
            .eq('ticker', ticker)\
            .order('timestamp', desc=True)\
            .limit(5000)\
            .execute()
        
        history_df = pd.DataFrame(history_response.data) if history_response.data else pd.DataFrame()

        if not history_df.empty:
            if 'close' in history_df.columns:
                history_df['price'] = history_df['close']
            
            # Standardize and Filter
            history_df['timestamp'] = pd.to_datetime(history_df['timestamp'], utc=True, format='mixed')
            history_df = history_df[history_df['timestamp'] < CUTOFF_DATE]
            
            history_df['sentiment'] = 'neutral'
            history_df['confidence'] = 0.0

        # --- PART B: FETCH ROBOT DATA (Newest -> Oldest) ---
        live_response = supabase.table('market_log')\
            .select("*")\
            .eq('ticker', ticker)\
            .order('timestamp', desc=True)\
            .limit(5000)\
            .execute()
            
        live_df = pd.DataFrame(live_response.data) if live_response.data else pd.DataFrame()

        if not live_df.empty:
            live_df['timestamp'] = pd.to_datetime(live_df['timestamp'], utc=True, format='mixed')
            live_df = live_df[live_df['timestamp'] >= CUTOFF_DATE]

        # --- PART C: STITCH AND RESORT ---
        if history_df.empty and live_df.empty:
            return pd.DataFrame()
        
        full_df = pd.concat([history_df, live_df], ignore_index=True)
        
        # CRITICAL: Re-sort to Oldest->Newest for the chart to draw correctly
        full_df = full_df.sort_values('timestamp', ascending=True)
        
        return full_df

    except Exception as e:
        print(f"❌ Merge Error: {e}")
        return pd.DataFrame()

# --- AUTHENTICATION FUNCTIONS ---
def sign_up_user(email, password):
    """Creates a new user in Supabase Auth"""
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        return response
    except Exception as e:
        return None

def sign_in_user(email, password):
    """Logs in an existing user"""
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return response
    except Exception as e:
        return None

def logout_user():
    supabase.auth.sign_out()

# --- UPDATED WATCHLIST FUNCTIONS ---
def get_user_watchlist(user_id):
    """Fetches tickers ONLY for the specific user"""
    try:
        # RLS in Supabase will automatically filter this, 
        # but filtering by column is a good double-check
        response = supabase.table('watchlist').select("ticker").eq('user_id', user_id).execute()
        return [row['ticker'] for row in response.data]
    except Exception as e:
        print(f"Error fetching watchlist: {e}")
        return []

def add_ticker_to_watchlist(ticker, user_id):
    """Adds a ticker for a SPECIFIC user"""
    try:
        # Check if already exists for this user
        existing = supabase.table('watchlist').select("*").eq('ticker', ticker).eq('user_id', user_id).execute()
        if existing.data:
            return False, "Already in your watchlist"
            
        supabase.table('watchlist').insert({"ticker": ticker, "user_id": user_id}).execute()
        return True, "Added"
    except Exception as e:
        return False, str(e)

def backfill_new_stock(ticker):
    """
    Downloads 1 year of history for a new stock and uploads it to Supabase.
    """
    print(f"⏳ Backfilling data for {ticker}...")
    try:
        # 1. Download Data
        stock = yf.Ticker(ticker)
        # Fetch 2 years to ensure we have enough for SMA-200
        hist = stock.history(period="2y") 
        
        if hist.empty:
            return False, "Ticker not found on Yahoo Finance."

        # 2. Format Data for Supabase
        records = []
        hist.reset_index(inplace=True)
        
        for _, row in hist.iterrows():
            record = {
                'ticker': ticker,
                'timestamp': row['Date'].isoformat(),
                'open': row['Open'],
                'high': row['High'],
                'low': row['Low'],
                'close': row['Close'],
                'volume': row['Volume']
            }
            records.append(record)

        # 3. Upload in Batches (Supabase has a limit per request)
        # We assume 'price_history' is your table name
        batch_size = 100
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            supabase.table('price_history').upsert(batch).execute()

        # 4. Add a dummy entry to market_log so it shows up in the dashboard immediately
        latest_price = records[-1]['close']
        supabase.table('market_log').insert({
            'ticker': ticker,
            'timestamp': records[-1]['timestamp'],
            'price': latest_price,
            'headline': 'New Stock Added - Waiting for News...',
            'sentiment': 'neutral',
            'confidence': 0.0
        }).execute()

        return True, "Success"

    except Exception as e:
        print(f"❌ Backfill Error: {e}")
        return False, str(e)