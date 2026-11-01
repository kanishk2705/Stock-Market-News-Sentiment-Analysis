import numpy as np
import pandas as pd
import pytest

import backtest_engine as bt


class SpyModel:
    """Records what the backtest lets the model see."""
    def __init__(self, forecast=None):
        self.fit_lengths, self.predict_lengths, self.forecast = [], [], forecast

    def fit(self, prices):
        self.fit_lengths.append(len(prices))

    def predict(self, prices):
        self.predict_lengths.append(len(prices))
        p = prices["price"].to_numpy()
        return self.forecast(p) if self.forecast else p[-1]


def make_series(n=400, seed=0):
    prices = 100 * np.exp(np.random.default_rng(seed).normal(0, 0.01, n).cumsum())
    return prices, pd.date_range("2024-01-01", periods=n, freq="B").values


def make_frame(prices, dates):
    return pd.DataFrame({"timestamp": dates, "price": prices})


def test_walk_forward_never_sees_the_day_it_predicts():
    prices, dates = make_series()
    spy = SpyModel()
    frame = bt.walk_forward(make_frame(prices, dates), spy, test_days=100, retrain_every=10)
    first_t = len(prices) - 100
    assert len(frame) == 100
    # prediction for day t is made from exactly t prices (indices 0..t-1)
    assert spy.predict_lengths == list(range(first_t, len(prices)))
    # retrained every 10 days, each time only on data before the predicted day
    assert spy.fit_lengths == list(range(first_t, len(prices), 10))
    assert (frame["actual"].values == prices[first_t:]).all()


def test_naive_model_has_zero_skill_and_no_trades():
    prices, dates = make_series()
    frame = bt.walk_forward(make_frame(prices, dates), SpyModel(), test_days=120)
    sim, m = bt.evaluate(frame)
    assert m["mae_model"] == pytest.approx(m["mae_naive"])
    assert m["skill_vs_naive"] == pytest.approx(0)
    assert m["dm_p_value"] == 1.0
    assert m["trades"] == 0 and m["strategy_return"] == 0


def test_perfect_foresight_is_detected_as_skill():
    prices, dates = make_series()
    lookup = {len(prices[:t]): prices[t] for t in range(len(prices))}
    oracle = SpyModel(forecast=lambda p: lookup[len(p)])
    _, m = bt.evaluate(bt.walk_forward(make_frame(prices, dates), oracle, test_days=200))
    assert m["mae_model"] == 0
    assert m["skill_vs_naive"] == 1
    assert m["dm_p_value"] < 0.001
    assert m["direction_accuracy"] == 100


def test_always_long_strategy_matches_buy_and_hold_minus_one_trade_cost():
    prices, dates = make_series()
    always_up = SpyModel(forecast=lambda p: p[-1] * 1.10)
    sim, m = bt.evaluate(bt.walk_forward(make_frame(prices, dates), always_up, test_days=150))
    assert m["trades"] == 1 and m["time_in_market"] == 100
    # the single entry cost is deducted from the first day's return
    r = sim["market_return"].values
    expected = ((1 + r[0] - bt.COST_PER_TRADE) * np.prod(1 + r[1:]) - 1) * 100
    assert m["strategy_return"] == pytest.approx(expected)


def test_max_drawdown_and_sharpe():
    assert bt.max_drawdown(np.array([1.0, 1.2, 0.9, 1.3])) == pytest.approx(-0.25)
    assert bt.sharpe(np.zeros(10)) == 0.0
    assert bt.sharpe(np.array([0.01, 0.02, 0.01, 0.02])) > 0


def test_too_little_history_raises():
    prices, dates = make_series(n=100)
    with pytest.raises(ValueError):
        bt.walk_forward(make_frame(prices, dates), SpyModel(), test_days=50)


def test_run_backtest_with_real_model_end_to_end():
    prices, dates = make_series(n=330)
    df = pd.DataFrame({"timestamp": dates, "price": prices})
    result = bt.run_backtest("TEST", df, test_days=60, retrain_every=30)
    assert len(result.frame) == 60
    assert 0 <= result.metrics["direction_accuracy"] <= 100
    assert bt.verdict(result.metrics).startswith("The model ")
    table = bt.summary_table([result])
    assert list(table["Ticker"]) == ["TEST"]
    assert bt.to_markdown(table).startswith("| Ticker |")


def test_features_never_use_future_prices():
    from prediction_engine import build_features
    prices, dates = make_series(n=300)
    base = build_features(make_frame(prices, dates))
    shocked = prices.copy()
    shocked[250:] *= 1.5                       # change everything from day 250 on
    after = build_features(make_frame(shocked, dates))
    feature_cols = [c for c in base.columns if c != "next_return"]
    pd.testing.assert_frame_equal(base.loc[:249, feature_cols], after.loc[:249, feature_cols])
    # only the target of day 249 (= return into day 250) may change
    assert base.loc[248, "next_return"] == after.loc[248, "next_return"]
    assert base.loc[249, "next_return"] != after.loc[249, "next_return"]


def test_sentiment_score_is_signed_confidence():
    from prediction_engine import build_features
    df = pd.DataFrame({"price": [10, 11, 12, 13.0], "sentiment": ["positive", "negative", "neutral", None],
                       "confidence": [0.9, 0.8, 0.95, None]})
    f = build_features(df)
    assert list(f["sentiment_score"]) == [0.9, -0.8, 0.0, 0.0]


@pytest.mark.parametrize("kind,use_sentiment", [("ridge", False), ("gbm", False), ("gbm", True)])
def test_returns_models_backtest_end_to_end(kind, use_sentiment):
    from prediction_engine import ReturnsModel
    prices, dates = make_series(n=400)
    df = make_frame(prices, dates)
    df["sentiment"], df["confidence"] = "neutral", 0.5
    result = bt.run_backtest("TEST", df, model=ReturnsModel(kind, use_sentiment), test_days=60, retrain_every=30)
    m = result.metrics
    # a returns model on a random walk should stay close to the naive forecast (no wild level errors)
    assert abs(m["skill_vs_naive"]) < 0.2
    assert result.frame["predicted"].between(prices.min() * 0.8, prices.max() * 1.2).all()


def test_returns_model_can_forecast_outside_training_range():
    """The V2 price-level Random Forest cannot do this - the root cause found in the phase-3 backtest."""
    from prediction_engine import ReturnsModel
    prices = 100 * np.exp(np.full(400, 0.004).cumsum())   # steady uptrend to new highs
    df = make_frame(prices, pd.date_range("2024-01-01", periods=400, freq="B").values)
    model = ReturnsModel("ridge")
    model.fit(df.iloc[:399])
    assert model.predict(df.iloc[:399]) > prices[:399].max()
    rf = bt.RandomForestPriceModel()
    rf.fit(df.iloc[:399])
    assert rf.predict(df.iloc[:399]) <= prices[:399].max()
