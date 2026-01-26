import os
import psycopg2
from dotenv import load_dotenv

# Load the secret password from .env file
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    """Establishes a connection to the Cloud Postgres DB."""
    try:
        # We need to ensure we are using the 'postgres' database
        conn = psycopg2.connect(DB_URL, sslmode='require')
        return conn
    except Exception as e:
        print(f"❌ Database Connection Failed: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn: return
    
    cursor = conn.cursor()
    
    # 1. LOG TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_log (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP,
            ticker TEXT,
            price REAL,
            headline TEXT,
            sentiment TEXT,
            confidence REAL
        );
    ''')

    # 2. WATCHLIST TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            ticker TEXT,
            UNIQUE(user_id, ticker)
        );
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Cloud Database Connected & Schema Verified")

# --- WATCHLIST FUNCTIONS ---
def add_ticker(user_id, ticker):
    conn = get_db_connection()
    if not conn: return False
    
    cursor = conn.cursor()
    clean_ticker = ticker.upper().strip()
    
    try:
        cursor.execute("INSERT INTO watchlist (user_id, ticker) VALUES (%s, %s)", (user_id, clean_ticker))
        conn.commit()
        print(f"✅ Added {clean_ticker} for {user_id}")
        return True
    except psycopg2.IntegrityError:
        conn.rollback() # Reset connection state
        print(f"⚠️ {clean_ticker} is already in {user_id}'s list.")
        return False
    finally:
        cursor.close()
        conn.close()

def get_user_watchlist(user_id):
    conn = get_db_connection()
    if not conn: return []
    
    cursor = conn.cursor()
    cursor.execute("SELECT ticker FROM watchlist WHERE user_id = %s", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_all_monitored_tickers():
    conn = get_db_connection()
    if not conn: return []
    
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT ticker FROM watchlist")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

# --- LOGGING FUNCTIONS ---
def save_log(data_list):
    conn = get_db_connection()
    if not conn: return
    
    cursor = conn.cursor()
    
    count = 0
    for item in data_list:
        try:
            # Postgres needs standard python datetime or string
            cursor.execute('''
                INSERT INTO market_log (timestamp, ticker, price, headline, sentiment, confidence)
                VALUES (NOW(), %s, %s, %s, %s, %s)
            ''', (item['Ticker'], item['Price'], item['Headline'], item['Sentiment'], item['Confidence']))
            count += 1
        except Exception as e:
            print(f"⚠️ Error saving {item['Ticker']}: {e}")
            
    conn.commit()
    cursor.close()
    conn.close()
    print(f"💾 Cloud Persistence: Saved {count} records to Postgres.")

if __name__ == "__main__":
    init_db()