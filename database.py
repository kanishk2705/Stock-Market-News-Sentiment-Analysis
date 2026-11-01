import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. LOAD SECRETS
# Locally they come from .env; on Streamlit Cloud they come from st.secrets.
load_dotenv()

PAGE_SIZE = 1000  # PostgREST returns at most 1000 rows per request


def _get_secret(name):
    value = os.getenv(name)
    if value:
        return value.strip().strip('"')
    try:
        import streamlit as st
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return None


URL = _get_secret("SUPABASE_URL")
# The robot (main.py / GitHub Actions) uses the service-role key so it can read every
# user's watchlist. The Streamlit app only ever uses the public anon key + user login.
SERVICE_KEY = _get_secret("SUPABASE_SERVICE_ROLE_KEY")
ANON_KEY = _get_secret("SUPABASE_KEY")

if not URL or not (ANON_KEY or SERVICE_KEY):
    raise ValueError("❌ Supabase Credentials missing. Check .env file.")


# 2. CLIENTS
# A Streamlit server runs one Python process for every visitor, so a module-level
# client would share one login session between all users. Inside Streamlit each
# browser session gets its own client; scripts (main.py, backfill) share one.
_script_client = None


def _in_streamlit_session():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx(suppress_warning=True) is not None
    except Exception:
        return False


def get_client() -> Client:
    global _script_client
    if _in_streamlit_session():
        import streamlit as st
        if "_supabase_client" not in st.session_state:
            st.session_state["_supabase_client"] = create_client(URL, ANON_KEY)
        return st.session_state["_supabase_client"]

    if _script_client is None:
        _script_client = create_client(URL, SERVICE_KEY or ANON_KEY)
    return _script_client


def _fetch_all(build_query):
    """Runs a select query page by page so results are not cut off at 1000 rows."""
    rows, start = [], 0
    while True:
        page = build_query().range(start, start + PAGE_SIZE - 1).execute().data or []
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        start += PAGE_SIZE


def _to_utc(series):
    return pd.to_datetime(series, utc=True, format="mixed")


def trading_date(series):
    """
    Older price_history rows store each day at the exchange's local midnight
    (e.g. 05:00 UTC for New York, 18:30 UTC the previous day for India).
    Shifting by 12h maps all of those - and plain UTC midnight - to the right day.
    """
    return (_to_utc(series) + pd.Timedelta(hours=12)).dt.date


# --- MARKET LOG (robot snapshots: price + headline + sentiment) ---
def insert_data(data_list):
    """
    Inserts data into the 'market_log' table.
    """
    if not data_list:
        return

    try:
        get_client().table('market_log').insert(data_list).execute()
        print(f"✅ Successfully inserted {len(data_list)} records to Cloud DB.")
    except Exception as e:
        print(f"❌ Database Insert Error: {e}")


def get_latest_data(ticker):
    """
    Fetches the single most recent record for a specific ticker.
    """
    try:
        response = get_client().table('market_log')\
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
    Fetches ALL market_log rows for a ticker (newest first).
    """
    try:
        data = _fetch_all(lambda: get_client().table('market_log')
                          .select("*").eq('ticker', ticker).order('timestamp', desc=True))
        return pd.DataFrame(data)
    except Exception as e:
        print(f"❌ History Fetch Error: {e}")
        return pd.DataFrame()


def get_portfolio_summary(tickers):
    """
    Fetches the LATEST market_log record for each of the given tickers.
    Used for the Dashboard Grid.
    """
    summary = []
    for ticker in tickers:
        latest = get_latest_data(ticker)
        if latest:
            summary.append(latest)
    return summary


def get_all_monitored_tickers():
    """
    Fetches the unique list of tickers across every user's watchlist (robot only).
    """
    try:
        data = _fetch_all(lambda: get_client().table('watchlist').select('ticker'))
        return sorted({item['ticker'] for item in data})
    except Exception as e:
        print(f"❌ Watchlist Fetch Error: {e}")
        return []


# --- LEGACY ADAPTERS ---
def init_db():
    print("✅ Cloud Database Connection Verified.")


def save_log(data):
    return insert_data(data)


# --- PRICE HISTORY (daily OHLCV) ---
def fetch_price_history(ticker):
    """
    Fetches the full OHLCV history from the 'price_history' table (oldest first).
    """
    try:
        data = _fetch_all(lambda: get_client().table('price_history')
                          .select("*").eq('ticker', ticker).order('timestamp', desc=False))
        return pd.DataFrame(data)
    except Exception as e:
        print(f"❌ Price History Fetch Error: {e}")
        return pd.DataFrame()


def merge_history_and_log(history_df, log_df):
    """
    Builds one row per trading day.
    - price: the official daily close from price_history, or the robot's last
      snapshot price for days that price_history does not cover yet.
    - sentiment / confidence / headline: the robot's last snapshot of that day.
    """
    frames = []
    if not history_df.empty:
        h = history_df.copy()
        h['date'] = trading_date(h['timestamp'])
        h['price'] = h['close']
        frames.append(h[['date', 'price']].assign(source='history'))

    news = pd.DataFrame(columns=['date', 'sentiment', 'confidence', 'headline'])
    if not log_df.empty:
        l = log_df.copy()
        l['ts'] = _to_utc(l['timestamp'])
        l['date'] = l['ts'].dt.date
        l = l.sort_values('ts').drop_duplicates('date', keep='last')
        # Weekend snapshots (manual runs) only repeat Friday's close - not a trading day
        trading = l[l['ts'].dt.day_of_week < 5]
        frames.append(trading[['date', 'price']].assign(source='log'))
        news = l[['date', 'sentiment', 'confidence', 'headline']]

    if not frames:
        return pd.DataFrame()

    prices = pd.concat(frames, ignore_index=True)
    prices = prices[pd.to_numeric(prices['price'], errors='coerce') > 0]
    # history wins over log when both have the same day
    prices['rank'] = prices['source'].map({'history': 0, 'log': 1})
    prices = prices.sort_values(['date', 'rank']).drop_duplicates('date', keep='first')

    full = prices.merge(news, on='date', how='left')
    full['sentiment'] = full['sentiment'].fillna('neutral')
    full['confidence'] = full['confidence'].fillna(0.0).astype(float)
    full['timestamp'] = pd.to_datetime(full['date'])
    full['price'] = full['price'].astype(float)
    return full.drop(columns=['rank', 'date']).sort_values('timestamp').reset_index(drop=True)


def fetch_unified_data(ticker):
    """
    Returns the full daily series for a ticker: price history stitched with the
    robot's news/sentiment snapshots, oldest first.
    """
    try:
        return merge_history_and_log(fetch_price_history(ticker), fetch_all_watchlist_data(ticker))
    except Exception as e:
        print(f"❌ Merge Error: {e}")
        return pd.DataFrame()


# --- AUTHENTICATION FUNCTIONS ---
def sign_up_user(email, password):
    """Creates a new user in Supabase Auth"""
    try:
        return get_client().auth.sign_up({"email": email, "password": password})
    except Exception as e:
        print(f"Sign up error: {e}")
        return None


def sign_in_user(email, password):
    """Logs in an existing user"""
    try:
        return get_client().auth.sign_in_with_password({"email": email, "password": password})
    except Exception as e:
        print(f"Sign in error: {e}")
        return None


def logout_user():
    try:
        get_client().auth.sign_out()
    except Exception as e:
        print(f"Sign out error: {e}")


# --- WATCHLIST FUNCTIONS ---
def get_user_watchlist(user_id):
    """Fetches tickers ONLY for the specific user"""
    try:
        # RLS in Supabase filters this automatically;
        # filtering by column is a second line of defence.
        response = get_client().table('watchlist').select("ticker").eq('user_id', user_id).execute()
        return [row['ticker'] for row in response.data]
    except Exception as e:
        print(f"Error fetching watchlist: {e}")
        return []


def add_ticker_to_watchlist(ticker, user_id):
    """Adds a ticker for a SPECIFIC user"""
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return False, "Please enter a ticker symbol"
    try:
        existing = get_client().table('watchlist').select("id").eq('ticker', ticker).eq('user_id', user_id).execute()
        if existing.data:
            return False, "Already in your watchlist"

        get_client().table('watchlist').insert({"ticker": ticker, "user_id": user_id}).execute()
        return True, "Added"
    except Exception as e:
        return False, str(e)


def remove_ticker_from_watchlist(ticker, user_id):
    try:
        get_client().table('watchlist').delete().eq('ticker', ticker).eq('user_id', user_id).execute()
        return True, "Removed"
    except Exception as e:
        return False, str(e)


def _latest_history_date(ticker):
    response = get_client().table('price_history').select('timestamp')\
        .eq('ticker', ticker).order('timestamp', desc=True).limit(1).execute()
    if response.data:
        day = trading_date(pd.Series([response.data[0]['timestamp']])).iloc[0]
        return pd.Timestamp(day, tz='UTC')
    return None


def history_to_records(ticker, hist):
    """Converts a yfinance history frame into price_history rows."""
    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.get_level_values(0)
    hist = hist.reset_index()
    date_col = 'Date' if 'Date' in hist.columns else 'Datetime'
    records = []
    for _, row in hist.dropna(subset=['Close']).iterrows():
        # Store the trading day at midnight UTC so every exchange lines up by date
        day = pd.Timestamp(row[date_col]).date()
        records.append({
            'ticker': ticker,
            'timestamp': f"{day.isoformat()}T00:00:00+00:00",
            'open': round(float(row['Open']), 4),
            'high': round(float(row['High']), 4),
            'low': round(float(row['Low']), 4),
            'close': round(float(row['Close']), 4),
            'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0,
        })
    return records


def backfill_new_stock(ticker, period="2y"):
    """
    Downloads daily history for a stock and upserts it into Supabase.
    If some history already exists, only the missing recent days are fetched,
    so calling this repeatedly keeps the data fresh ("self-healing").
    """
    print(f"⏳ Backfilling data for {ticker}...")
    try:
        last = _latest_history_date(ticker)
        stock = yf.Ticker(ticker)
        if last is not None:
            if last.date() >= (datetime.now(timezone.utc) - timedelta(days=1)).date():
                return True, "Up to date"
            hist = stock.history(start=(last - timedelta(days=5)).strftime('%Y-%m-%d'), auto_adjust=False)
        else:
            # 2 years is enough for SMA-200 and the prediction window
            hist = stock.history(period=period, auto_adjust=False)

        if hist.empty:
            return (True, "No new rows") if last is not None else (False, "Ticker not found on Yahoo Finance.")

        records = history_to_records(ticker, hist)

        # Upload in batches; (ticker, timestamp) is unique so re-runs never duplicate
        for i in range(0, len(records), 500):
            get_client().table('price_history')\
                .upsert(records[i:i + 500], on_conflict='ticker,timestamp').execute()

        # Seed market_log so a brand-new stock shows up in the dashboard immediately
        if get_latest_data(ticker) is None:
            get_client().table('market_log').insert({
                'ticker': ticker,
                'timestamp': records[-1]['timestamp'],
                'price': records[-1]['close'],
                'headline': 'New Stock Added - Waiting for News...',
                'sentiment': 'neutral',
                'confidence': 0.0
            }).execute()

        print(f"✅ {ticker}: upserted {len(records)} rows")
        return True, f"Synced {len(records)} rows"

    except Exception as e:
        print(f"❌ Backfill Error: {e}")
        return False, str(e)


# --- PUBLIC DEMO ACCOUNT ---
DEMO_TICKERS = ["NVDA", "AAPL", "TSLA", "VOO", "INFY.NS", "HDFCBANK.NS", "WAAREEENER.NS", "KO"]


def reset_demo_account(email=None, password=None, tickers=DEMO_TICKERS):
    """
    Restores the shared demo login (password + default watchlist) so a visitor
    who changes either cannot lock out the next one. Robot only (service-role key).
    """
    import requests

    email = email or _get_secret("DEMO_EMAIL")
    password = password or _get_secret("DEMO_PASSWORD")
    if not (email and password and SERVICE_KEY):
        return False, "Demo account not configured"

    headers = {"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}"}
    users = requests.get(f"{URL}/auth/v1/admin/users?per_page=1000", headers=headers, timeout=30).json()["users"]
    user = next((u for u in users if u["email"].lower() == email.lower()), None)
    if user:
        requests.put(f"{URL}/auth/v1/admin/users/{user['id']}", headers=headers,
                     json={"password": password, "email_confirm": True}, timeout=30).raise_for_status()
        user_id = user["id"]
    else:
        r = requests.post(f"{URL}/auth/v1/admin/users", headers=headers,
                          json={"email": email, "password": password, "email_confirm": True}, timeout=30)
        r.raise_for_status()
        user_id = r.json()["id"]

    client = get_client()
    client.table('watchlist').delete().eq('user_id', user_id).execute()
    client.table('watchlist').insert([{"user_id": user_id, "ticker": t} for t in tickers]).execute()
    return True, f"Demo account {email} reset with {len(tickers)} tickers"
