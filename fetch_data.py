import re
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import requests
import yfinance as yf

from database import get_all_monitored_tickers  # <-- Imports from your DB file
from market_utils import get_currency_symbol

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'}

# yfinance's Ticker.news stopped returning articles in 2026, so headlines come from
# RSS feeds instead: Google News (searched by company name) with Yahoo's per-ticker feed as backup.
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
YAHOO_RSS = "https://feeds.finance.yahoo.com/rss/2.0/headline"

# Titles of live-quote pages, e.g. "HDFC Bank Share Price - Live NSE/BSE Updates" or
# "Infosys Limited (INFY) stock price, news, quote and history"
QUOTE_PAGE = re.compile(r"\b(stock|share) price\b.*\b(news|quote|live|history|chart|today)\b", re.IGNORECASE)


def extract_headline(story):
    """Yahoo has used both a flat and a nested ('content') news format."""
    content = story.get('content') if isinstance(story.get('content'), dict) else story
    return content.get('title')


def parse_rss(xml_bytes, strip_source=False):
    """Returns [{'title', 'published'}] newest first from an RSS document."""
    items = []
    for item in ET.fromstring(xml_bytes).findall('.//item'):
        title = (item.findtext('title') or '').strip()
        if strip_source and ' - ' in title:
            # Google News appends " - Publisher" to every title
            title = title.rsplit(' - ', 1)[0].strip()
        try:
            published = parsedate_to_datetime(item.findtext('pubDate'))
        except Exception:
            published = None
        # Skip quote-page listings ("... Stock Price, News, Quote & History") - they are not news
        if title and not QUOTE_PAGE.search(title):
            items.append({'title': title, 'published': published})
    items.sort(key=lambda x: x['published'].timestamp() if x['published'] else 0, reverse=True)
    return items


def get_company_name(stock, ticker):
    try:
        info = stock.info
        return info.get('shortName') or info.get('longName') or ticker
    except Exception:
        return ticker


def fetch_headlines(ticker, company_name=None, limit=5):
    """Most recent headlines for a stock, newest first."""
    name = (company_name or ticker).replace(' Limited', '').replace(' Ltd.', '').replace(' Inc.', '').strip()
    sources = [
        (GOOGLE_NEWS_RSS, {"q": f'"{name}" stock when:3d', "hl": "en-US", "gl": "US", "ceid": "US:en"}, True),
        (YAHOO_RSS, {"s": ticker, "region": "US", "lang": "en-US"}, False),
    ]
    for url, params, strip in sources:
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=15)
            r.raise_for_status()
            items = parse_rss(r.content, strip_source=strip)
            if items:
                return [i['title'] for i in items[:limit]]
        except Exception as e:
            print(f"⚠️ News source failed for {ticker}: {e}")
    return []


def fetch_portfolio_data():
    print(f"--- 📈 DYNAMIC MARKET SCAN: {datetime.now().strftime('%Y-%m-%d %H:%M')} ---")

    # 1. GET TARGETS FROM DB
    target_tickers = get_all_monitored_tickers()

    if not target_tickers:
        print("⚠️ No stocks found in Supabase watchlist. Add stocks via the App first!")
        return []

    print(f"🔍 Monitoring {len(target_tickers)} unique assets: {target_tickers}")
    all_data = []

    for ticker_symbol in target_tickers:
        stock_data = {"Ticker": ticker_symbol, "Price": 0.0, "Headline": "N/A", "Headlines": []}
        currency = get_currency_symbol(ticker_symbol)
        stock = yf.Ticker(ticker_symbol)

        # BLOCK A: Get Price
        try:
            price = stock.fast_info['last_price']
            stock_data["Price"] = float(price)
            print(f"✅ {ticker_symbol}: {currency}{price:,.2f}", end=" | ")
        except Exception as e:
            print(f"⚠️ {ticker_symbol} Price Failed ({e})", end=" | ")

        # BLOCK B: Get News
        headlines = fetch_headlines(ticker_symbol, get_company_name(stock, ticker_symbol))
        if headlines:
            stock_data["Headline"] = headlines[0]
            stock_data["Headlines"] = headlines
            print(f"📰 {headlines[0][:30]}...")
        else:
            print("📭 No news")

        if stock_data["Price"] > 0:
            all_data.append(stock_data)

    return all_data


if __name__ == "__main__":
    # Test run
    data = fetch_portfolio_data()
