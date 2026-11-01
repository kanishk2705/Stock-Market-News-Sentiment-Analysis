import numpy as np
import pandas as pd

from analysis_engine import calculate_technical_indicators, get_market_signal
from prediction_engine import prepare_sliding_window, predict_next_day_price


def make_prices(values):
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=len(values), freq="D"),
        "price": values,
    })


def test_sma_matches_manual_mean_and_has_no_lookahead():
    df = calculate_technical_indicators(make_prices(np.arange(1, 301, dtype=float)))
    assert df["SMA_50"].iloc[49] == np.mean(np.arange(1, 51))
    assert df["SMA_200"].iloc[-1] == np.mean(np.arange(101, 301))
    # Before a full window exists the SMA must stay empty, not be filled from the future
    assert df["SMA_50"].iloc[:49].isna().all()
    assert df["SMA_200"].iloc[:199].isna().all()


def test_rsi_bounds_and_extremes():
    rising = calculate_technical_indicators(make_prices(np.arange(1, 101, dtype=float)))
    falling = calculate_technical_indicators(make_prices(np.arange(100, 0, -1, dtype=float)))
    assert rising["RSI"].iloc[-1] > 99
    assert falling["RSI"].iloc[-1] < 1

    noisy = calculate_technical_indicators(make_prices(100 + np.random.default_rng(0).normal(0, 1, 300).cumsum()))
    assert noisy["RSI"].between(0, 100).all()


def test_market_signal_rules():
    assert "Overbought" in get_market_signal({"RSI": 80, "price": 10, "SMA_50": 5, "SMA_200": 4})
    assert "Bullish" in get_market_signal({"RSI": 50, "price": 10, "SMA_50": 5, "SMA_200": 4})
    assert "Bearish" in get_market_signal({"RSI": 50, "price": 3, "SMA_50": 5, "SMA_200": 4})
    assert get_market_signal({"RSI": 50, "price": 10, "SMA_50": float("nan"), "SMA_200": float("nan")}) == "⚖️ Market Neutral"


def test_sliding_window_shapes():
    X, y = prepare_sliding_window(np.arange(10), window_size=3)
    assert X.shape == (7, 3)
    assert list(X[0]) == [0, 1, 2] and y[0] == 3
    assert y[-1] == 9


def test_prediction_needs_enough_data():
    price, msg = predict_next_day_price("X", make_prices(np.arange(50, dtype=float)))
    assert price is None and "70" in msg


def test_prediction_returns_price_and_signal_without_mutating_input():
    df = make_prices(100 + np.sin(np.arange(200) / 5) * 5)
    df["timestamp"] = df["timestamp"].astype(str)
    before = df.copy()
    price, signal = predict_next_day_price("X", df)
    assert 90 < price < 110
    assert signal in ("🟢 STRONG BUY", "🔴 STRONG SELL", "⚪ HOLD")
    pd.testing.assert_frame_equal(df, before)
