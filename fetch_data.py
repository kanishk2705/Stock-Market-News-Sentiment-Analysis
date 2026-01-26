import yfinance as yf
from datetime import datetime
from database import get_all_monitored_tickers  # <-- Imports from your DB file

def get_currency_symbol(ticker):
    if ticker.startswith("^NS") or ticker.startswith("^BS") or ticker.endswith(".NS") or ticker.endswith(".BO"):
        return "₹"
    return "$"

def fetch_portfolio_data():
    print(f"--- 📈 DYNAMIC MARKET SCAN: {datetime.now().strftime('%Y-%m-%d %H:%M')} ---")
    
    # 1. GET TARGETS FROM DB (The Big Change)
    target_tickers = get_all_monitored_tickers()
    
    if not target_tickers:
        print("⚠️ No stocks found in Supabase watchlist. Add stocks via the App first!")
        return []

    print(f"🔍 Monitoring {len(target_tickers)} unique assets: {target_tickers}")
    all_data = []

    for ticker_symbol in target_tickers:
        stock_data = {"Ticker": ticker_symbol, "Price": 0.0, "Headline": "N/A"}
        currency = get_currency_symbol(ticker_symbol)
        
        # BLOCK A: Get Price
        try:
            stock = yf.Ticker(ticker_symbol)
            price = stock.fast_info['last_price']
            stock_data["Price"] = price
            print(f"✅ {ticker_symbol}: {currency}{price:,.2f}", end=" | ")
        except:
            print(f"⚠️ {ticker_symbol} Price Failed", end=" | ")

        # BLOCK B: Get News
        try:
            news = stock.news
            if news:
                first_story = news[0]
                # Logic to handle nested Yahoo JSON
                if 'content' in first_story and 'title' in first_story['content']:
                    headline = first_story['content']['title']
                elif 'title' in first_story:
                    headline = first_story['title']
                else:
                    headline = "Format Unknown"
                
                stock_data["Headline"] = headline
                print(f"📰 {headline[:30]}...")
            else:
                print("📭 No news")
        except:
            print(f"⚠️ News Error")

        if stock_data["Price"] > 0:
            all_data.append(stock_data)

    return all_data

if __name__ == "__main__":
    # Test run
    data = fetch_portfolio_data()