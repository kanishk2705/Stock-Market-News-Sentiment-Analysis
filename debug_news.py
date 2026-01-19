import yfinance as yf
import json

ticker = yf.Ticker("NVDA")
news_list = ticker.news

if news_list:
    first_news = news_list[0]
    print("\n🔍 RAW NEWS DATA KEYS:")
    print(list(first_news.keys()))

    print("\n📄 FULL OBJECT:")
    print(json.dumps(first_news, indent=2))

else:
    print("❌ No news found to inspect.")