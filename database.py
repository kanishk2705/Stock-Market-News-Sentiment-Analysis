import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

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
        
        # Sort by time (newest first)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
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