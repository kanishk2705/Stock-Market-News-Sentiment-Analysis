"""
Gap-fill tool: brings price_history up to date for every ticker in any watchlist.
Safe to re-run - rows are upserted on (ticker, timestamp), so nothing is duplicated.

Usage:  python backfill_manager.py            # top up missing days only
        python backfill_manager.py --full     # re-download 5 years for every ticker
"""
import sys
import time

import yfinance as yf

from database import get_all_monitored_tickers, backfill_new_stock, history_to_records, get_client

CHUNK_SIZE = 500


def full_backfill(ticker, period="5y"):
    print(f"\n⏳ Downloading {period} history for: {ticker}...")
    hist = yf.Ticker(ticker).history(period=period, auto_adjust=False)
    if hist.empty:
        print(f"❌ No data found for {ticker}.")
        return
    records = history_to_records(ticker, hist)
    for i in range(0, len(records), CHUNK_SIZE):
        get_client().table('price_history')\
            .upsert(records[i:i + CHUNK_SIZE], on_conflict='ticker,timestamp').execute()
        time.sleep(0.1)
    print(f"🎉 {ticker}: Fully Synced ({len(records)} records).")


def run_backfill_pipeline(full=False):
    print("🚀 STARTING GAP-FILL OPERATION...")
    tickers = get_all_monitored_tickers()

    if not tickers:
        print("❌ No tickers found.")
        return

    print(f"📋 Target Watchlist: {tickers}")

    for ticker in tickers:
        try:
            if full:
                full_backfill(ticker)
            else:
                ok, msg = backfill_new_stock(ticker)
                print(f"{'✅' if ok else '❌'} {ticker}: {msg}")
        except Exception as e:
            print(f"❌ Critical Error for {ticker}: {e}")

    print("\n✅ GAP FILL COMPLETE.")


if __name__ == "__main__":
    run_backfill_pipeline(full="--full" in sys.argv)
