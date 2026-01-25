import sqlite3
from datetime import datetime

DB_NAME = "finance.db"

def init_db():
    """Creates the database table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create a table to store history
    # We store: Date, Ticker, Price, Sentiment Label, and Confidence Score
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            ticker TEXT,
            price REAL,
            headline TEXT,
            sentiment TEXT,
            confidence REAL
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized (finance.db)")

def save_log(data_list):
    """Saves a list of enriched stock data to the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    count = 0
    for item in data_list:
        cursor.execute('''
            INSERT INTO market_log (timestamp, ticker, price, headline, sentiment, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            current_time, 
            item['Ticker'], 
            item['Price'], 
            item['Headline'], 
            item['Sentiment'], 
            item['Confidence']
        ))
        count += 1
        
    conn.commit()
    conn.close()
    print(f"💾 Saved {count} records to Database.")

def fetch_history(ticker):
    """(Optional) Retrieve history for a specific stock."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT timestamp, price, sentiment FROM market_log WHERE ticker = ? ORDER BY timestamp DESC", (ticker,))
    rows = cursor.fetchall()
    conn.close()
    return rows

if __name__ == "__main__":
    init_db()