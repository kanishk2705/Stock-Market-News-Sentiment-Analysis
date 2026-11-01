from datetime import date

import pandas as pd

import database


def test_trading_date_handles_every_stored_timestamp_style():
    stamps = pd.Series([
        "2026-02-06T00:00:00+00:00",  # UTC midnight (new rows)
        "2026-02-10T05:00:00+00:00",  # New York midnight
        "2026-02-11T18:30:00+00:00",  # India midnight of 12 Feb
    ])
    assert list(database.trading_date(stamps)) == [date(2026, 2, 6), date(2026, 2, 10), date(2026, 2, 12)]


def test_merge_prefers_history_and_extends_with_log_without_cutoff():
    history = pd.DataFrame({
        "ticker": "AAPL",
        "timestamp": ["2026-06-01T00:00:00+00:00", "2026-06-02T00:00:00+00:00"],
        "close": [100.0, 101.0],
    })
    log = pd.DataFrame({
        "ticker": "AAPL",
        "timestamp": ["2026-06-02T21:00:00", "2026-06-02T22:00:00", "2026-06-03T21:00:00"],
        "price": [999.0, 998.0, 103.0],
        "headline": ["old", "latest of day 2", "day 3"],
        "sentiment": ["negative", "positive", "neutral"],
        "confidence": [0.9, 0.8, 0.7],
    })
    merged = database.merge_history_and_log(history, log)

    assert list(merged["price"]) == [100.0, 101.0, 103.0]          # history wins, log extends
    assert merged["timestamp"].is_monotonic_increasing
    day2 = merged.iloc[1]
    assert day2["sentiment"] == "positive" and day2["headline"] == "latest of day 2"
    assert merged.iloc[0]["sentiment"] == "neutral" and merged.iloc[0]["confidence"] == 0.0


def test_merge_with_only_one_source():
    log = pd.DataFrame({"ticker": "X", "timestamp": ["2026-01-01T10:00:00"], "price": [5.0],
                        "headline": ["h"], "sentiment": ["neutral"], "confidence": [0.5]})
    assert len(database.merge_history_and_log(pd.DataFrame(), log)) == 1
    assert database.merge_history_and_log(pd.DataFrame(), pd.DataFrame()).empty


def test_history_to_records_normalises_dates_and_skips_gaps():
    idx = pd.DatetimeIndex(["2026-10-22", "2026-10-23", "2026-10-24"], tz="Asia/Kolkata", name="Date")
    hist = pd.DataFrame({"Open": [1, 2, 3], "High": [1, 2, 3], "Low": [1, 2, 3],
                         "Close": [1.5, float("nan"), 3.5], "Volume": [10, 20, float("nan")]}, index=idx)
    records = database.history_to_records("INFY.NS", hist)
    assert [r["timestamp"] for r in records] == ["2026-10-22T00:00:00+00:00", "2026-10-24T00:00:00+00:00"]
    assert records[1]["volume"] == 0


def test_each_streamlit_session_gets_its_own_client(monkeypatch):
    """Regression test: one module-level client used to share a login across all visitors."""
    import streamlit as st

    sessions = [{}, {}]
    current = {"i": 0}

    class FakeState:
        def __contains__(self, k): return k in sessions[current["i"]]
        def __getitem__(self, k): return sessions[current["i"]][k]
        def __setitem__(self, k, v): sessions[current["i"]][k] = v

    monkeypatch.setattr(database, "_in_streamlit_session", lambda: True)
    monkeypatch.setattr(st, "session_state", FakeState())

    first = database.get_client()
    assert database.get_client() is first          # stable within one session
    current["i"] = 1
    second = database.get_client()
    assert second is not first                     # isolated between sessions


def test_weekend_snapshots_do_not_create_trading_days():
    history = pd.DataFrame({"timestamp": ["2026-10-30T00:00:00+00:00"], "close": [204.64]})
    log = pd.DataFrame({
        "timestamp": ["2026-10-30T21:00:00", "2026-10-31T15:00:00"],   # Friday, Saturday
        "price": [204.64, 204.64], "headline": ["fri", "sat"],
        "sentiment": ["neutral", "positive"], "confidence": [0.5, 0.9],
    })
    merged = database.merge_history_and_log(history, log)
    assert list(merged["timestamp"].dt.day_name()) == ["Friday"]
