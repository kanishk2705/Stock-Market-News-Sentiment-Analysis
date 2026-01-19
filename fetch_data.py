import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. DEFINE YOUR PORTFOLIO
my_portfolio = {
    "US Tech": ["NVDA", "TSLA", "SOXX", "VGT"],
    "US Indices/Banks": ["BAC", "VOO", "VEU"],
    "Indian Market": ["^NSEI", "^BSESN"]
}

def get_currency_symbol(ticker):
    # Detect Indian tickers (Nifty/Sensex or ending in .NS/.BO)
    if ticker.startswith("^NS") or ticker.startswith("^BS") or ticker.endswith(".NS") or ticker.endswith(".BO"):
        return "₹"
    return "$"

def fetch_portfolio_data():
    print(f"--- 📈 PORTFOLIO REPORT: {datetime.now().strftime('%Y-%m-%d %H:%M')} ---")
    
    all_data = []

    for category, tickers in my_portfolio.items():
        print(f"\nScanning {category}...")
        
        for ticker_symbol in tickers:
            stock_data = {"Ticker": ticker_symbol, "Price": 0.0, "Headline": "N/A"}
            currency = get_currency_symbol(ticker_symbol)
            
            # BLOCK A: Get Price
            try:
                stock = yf.Ticker(ticker_symbol)
                price = stock.fast_info['last_price']
                stock_data["Price"] = price
                print(f"✅ {ticker_symbol}: {currency}{price:,.2f}", end=" | ")
            except Exception:
                print(f"⚠️ {ticker_symbol} Price Failed", end=" | ")

            # BLOCK B: Get News (Fixed for Nested 'content' Structure)
            try:
                news = stock.news
                if news:
                    first_story = news[0]
                    
                    # Logic: Check if 'title' is inside 'content' (New Yahoo Format)
                    if 'content' in first_story and 'title' in first_story['content']:
                        headline = first_story['content']['title']
                    
                    # Fallback: Check if 'title' is at the top level (Old Yahoo Format)
                    elif 'title' in first_story:
                        headline = first_story['title']
                    
                    else:
                        headline = "Format Unknown"

                    stock_data["Headline"] = headline
                    print(f"📰 {headline[:40]}...")
                else:
                    print("📭 No news")
            except Exception as e:
                print(f"⚠️ News Error: {e}")

            if stock_data["Price"] > 0:
                all_data.append(stock_data)

    return all_data

if __name__ == "__main__":
    data = fetch_portfolio_data()
    
    # 3. EXPORT
    if data:
        df = pd.DataFrame(data)
        print("\n--- 💾 DATA PREVIEW ---")
        print(df[['Ticker', 'Price', 'Headline']].head(10))