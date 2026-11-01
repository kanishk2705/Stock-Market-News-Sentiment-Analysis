"""
Walk-forward backtest for the next-day price forecast.

For every day t in the test period the model only sees prices up to day t-1,
predicts day t, and is compared with:
  - the naive forecast   (tomorrow's price = today's price)
  - the majority guess   (always predict "up")
  - buy & hold           (for the trading simulation)

Usage:  python backtest_engine.py              # all watchlist tickers -> results/
        python backtest_engine.py NVDA INFY.NS # selected tickers
        python backtest_engine.py --compare    # compare all candidate models
"""
import math
import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd

from prediction_engine import WINDOW_SIZE, SIGNAL_THRESHOLD, fit_model, predict_next

TRADING_DAYS = 252
COST_PER_TRADE = 0.001  # 0.1% per position change (brokerage + slippage)


class RandomForestPriceModel:
    """The original V2 model: Random Forest on raw 60-day price windows."""
    name = "Random Forest on prices (V2)"

    def fit(self, history):
        self.model = fit_model(history["price"].values)

    def predict(self, history):
        return predict_next(self.model, history["price"].values)


@dataclass
class BacktestResult:
    ticker: str
    frame: pd.DataFrame     # one row per test day
    metrics: dict


def walk_forward(data, model, test_days=252, retrain_every=21, min_train=WINDOW_SIZE + 60):
    """
    `data`: one row per trading day, oldest first, with 'timestamp' and 'price'
    (plus optional extra columns such as 'sentiment' / 'confidence').
    Returns a DataFrame with the prediction for each test day. Models only ever
    receive `data.iloc[:t]`, i.e. rows strictly before the day being predicted,
    and are re-trained every `retrain_every` days.
    """
    data = data.reset_index(drop=True)
    prices = data["price"].to_numpy(dtype=float)
    dates = pd.to_datetime(data["timestamp"]).values
    n = len(prices)
    start = max(n - test_days, min_train)
    if start >= n:
        raise ValueError(f"Not enough history: {n} days (need > {min_train})")

    rows = []
    for t in range(start, n):
        history = data.iloc[:t]                 # strictly data before day t
        if (t - start) % retrain_every == 0:
            model.fit(history)
        rows.append({
            "date": dates[t],
            "prev_price": prices[t - 1],
            "actual": prices[t],
            "predicted": model.predict(history),
            "naive": prices[t - 1],
        })
    return pd.DataFrame(rows)


def diebold_mariano(errors_a, errors_b):
    """
    Diebold-Mariano test (absolute-error loss, 1-step horizon).
    Negative statistic = model A has smaller errors. Returns (stat, two-sided p-value).
    """
    d = np.abs(errors_a) - np.abs(errors_b)
    if len(d) < 2 or d.std(ddof=1) == 0:
        return 0.0, 1.0
    stat = d.mean() / (d.std(ddof=1) / math.sqrt(len(d)))
    p_value = math.erfc(abs(stat) / math.sqrt(2))
    return float(stat), float(p_value)


def max_drawdown(equity):
    peak = np.maximum.accumulate(equity)
    return float((equity / peak - 1).min())


def sharpe(daily_returns):
    sd = np.std(daily_returns, ddof=1)
    return float(np.mean(daily_returns) / sd * math.sqrt(TRADING_DAYS)) if sd > 0 else 0.0


def simulate_strategy(frame, threshold=SIGNAL_THRESHOLD, cost=COST_PER_TRADE):
    """
    Long for day t when the forecast made before day t expects a rise above `threshold`,
    otherwise in cash. Trading costs are charged on every position change.
    """
    f = frame.copy()
    f["market_return"] = f["actual"] / f["prev_price"] - 1
    f["position"] = (f["predicted"] > f["prev_price"] * (1 + threshold)).astype(float)
    trades = f["position"].diff().abs().fillna(f["position"])
    f["strategy_return"] = f["position"] * f["market_return"] - trades * cost
    f["strategy_equity"] = (1 + f["strategy_return"]).cumprod()
    f["buy_hold_equity"] = (1 + f["market_return"]).cumprod()
    return f, int(trades.sum())


def evaluate(frame):
    """Forecast accuracy + trading metrics for a walk-forward frame."""
    err_model = frame["predicted"] - frame["actual"]
    err_naive = frame["naive"] - frame["actual"]
    actual_move = np.sign(frame["actual"] - frame["prev_price"])
    predicted_move = np.sign(frame["predicted"] - frame["prev_price"])
    moved = actual_move != 0

    mae_model, mae_naive = err_model.abs().mean(), err_naive.abs().mean()
    dm_stat, dm_p = diebold_mariano(err_model.values, err_naive.values)
    sim, n_trades = simulate_strategy(frame)

    years = len(sim) / TRADING_DAYS
    strat_total = sim["strategy_equity"].iloc[-1] - 1
    bh_total = sim["buy_hold_equity"].iloc[-1] - 1

    metrics = {
        "test_days": len(frame),
        "start": frame["date"].iloc[0],
        "end": frame["date"].iloc[-1],
        "mae_model": mae_model,
        "mae_naive": mae_naive,
        "rmse_model": math.sqrt((err_model ** 2).mean()),
        "rmse_naive": math.sqrt((err_naive ** 2).mean()),
        "mape_model": (err_model.abs() / frame["actual"]).mean() * 100,
        "mape_naive": (err_naive.abs() / frame["actual"]).mean() * 100,
        # > 0 means the model beats the naive forecast
        "skill_vs_naive": 1 - mae_model / mae_naive if mae_naive else 0.0,
        "dm_stat": dm_stat,
        "dm_p_value": dm_p,
        "direction_accuracy": (predicted_move[moved] == actual_move[moved]).mean() * 100,
        "always_up_accuracy": (actual_move[moved] > 0).mean() * 100,
        "predicted_up_share": (predicted_move[moved] > 0).mean() * 100,
        "strategy_return": strat_total * 100,
        "buy_hold_return": bh_total * 100,
        "strategy_cagr": ((1 + strat_total) ** (1 / years) - 1) * 100 if years > 0 else 0.0,
        "buy_hold_cagr": ((1 + bh_total) ** (1 / years) - 1) * 100 if years > 0 else 0.0,
        "strategy_sharpe": sharpe(sim["strategy_return"]),
        "buy_hold_sharpe": sharpe(sim["market_return"]),
        "strategy_max_dd": max_drawdown(sim["strategy_equity"].values) * 100,
        "buy_hold_max_dd": max_drawdown(sim["buy_hold_equity"].values) * 100,
        "trades": n_trades,
        "time_in_market": sim["position"].mean() * 100,
    }
    return sim, metrics


def run_backtest(ticker, df, model=None, test_days=252, retrain_every=21):
    """df needs 'timestamp' and 'price' columns (e.g. database.fetch_unified_data)."""
    df = df.dropna(subset=["price"]).sort_values("timestamp")
    if model is None:
        from prediction_engine import make_production_model
        model = make_production_model()
    frame = walk_forward(df, model, test_days, retrain_every)
    sim, metrics = evaluate(frame)
    return BacktestResult(ticker, sim, metrics)


def verdict(m):
    """Plain-English summary of a metrics dict."""
    beats = m["skill_vs_naive"] > 0 and m["dm_p_value"] < 0.05
    if beats:
        accuracy = "beats the naive forecast with statistical significance"
    elif m["dm_p_value"] < 0.05:
        accuracy = "is significantly WORSE than simply predicting today's price"
    else:
        accuracy = "is not significantly different from simply predicting today's price"
    return (f"The model {accuracy} (MAE {m['mae_model']:.2f} vs {m['mae_naive']:.2f}, "
            f"DM p = {m['dm_p_value']:.3f}). It called the direction right "
            f"{m['direction_accuracy']:.1f}% of the time vs {m['always_up_accuracy']:.1f}% for 'always up'.")


SUMMARY_COLUMNS = {
    "ticker": "Ticker", "mae_model": "MAE model", "mae_naive": "MAE naive",
    "skill_vs_naive": "Skill vs naive", "dm_p_value": "DM p-value",
    "direction_accuracy": "Direction acc. %", "always_up_accuracy": "Always-up acc. %",
    "strategy_return": "Strategy return %", "buy_hold_return": "Buy & hold %",
    "strategy_sharpe": "Strategy Sharpe", "buy_hold_sharpe": "B&H Sharpe",
}


def to_markdown(table):
    fmt = lambda v: f"{v:.2f}" if isinstance(v, (float, np.floating)) else str(v)
    lines = ["| " + " | ".join(table.columns) + " |", "|" + "---|" * len(table.columns)]
    lines += ["| " + " | ".join(fmt(v) for v in row) + " |" for row in table.itertuples(index=False)]
    return "\n".join(lines)


def summary_table(results):
    rows = [{"ticker": r.ticker, **r.metrics} for r in results]
    return pd.DataFrame(rows)[list(SUMMARY_COLUMNS)].rename(columns=SUMMARY_COLUMNS)


def candidate_models():
    from prediction_engine import ReturnsModel
    return [RandomForestPriceModel(), ReturnsModel("ridge"), ReturnsModel("gbm"), ReturnsModel("gbm", use_sentiment=True)]


def pooled_stats(results):
    """Aggregates one model's results over all tickers."""
    from scipy.stats import binomtest
    frames = pd.concat([r.frame for r in results])
    moved = frames["actual"] != frames["prev_price"]
    hits = int(((frames["predicted"] > frames["prev_price"]) == (frames["actual"] > frames["prev_price"]))[moved].sum())
    n = int(moved.sum())
    m = [r.metrics for r in results]
    return {
        "Tickers": len(results),
        "Predictions": n,
        "Mean skill vs naive": np.mean([x["skill_vs_naive"] for x in m]),
        "Sig. better than naive": sum(x["skill_vs_naive"] > 0 and x["dm_p_value"] < 0.05 for x in m),
        "Sig. worse than naive": sum(x["skill_vs_naive"] < 0 and x["dm_p_value"] < 0.05 for x in m),
        "Direction acc. %": hits / n * 100,
        "Binomial p (vs 50%)": binomtest(hits, n, 0.5, alternative="greater").pvalue,
        "Mean strategy return %": np.mean([x["strategy_return"] for x in m]),
        "Mean buy & hold %": np.mean([x["buy_hold_return"] for x in m]),
        "Mean strategy Sharpe": np.mean([x["strategy_sharpe"] for x in m]),
        "Mean B&H Sharpe": np.mean([x["buy_hold_sharpe"] for x in m]),
        "Beat B&H (tickers)": sum(x["strategy_return"] > x["buy_hold_return"] for x in m),
    }


def compare_models(tickers=None, test_days=252):
    import os
    from database import get_all_monitored_tickers, fetch_unified_data

    tickers = tickers or get_all_monitored_tickers()
    data = {t: fetch_unified_data(t) for t in tickers}
    rows, per_ticker = [], []
    for model in candidate_models():
        results = []
        for t, df in data.items():
            try:
                results.append(run_backtest(t, df, model=model, test_days=test_days))
            except Exception as e:
                print(f"⚠️ {model.name} / {t}: skipped ({e})")
        stats = pooled_stats(results)
        rows.append({"Model": model.name, **stats})
        per_ticker += [{"Model": model.name, "Ticker": r.ticker,
                        "Skill vs naive": r.metrics["skill_vs_naive"], "DM p-value": r.metrics["dm_p_value"],
                        "Direction acc. %": r.metrics["direction_accuracy"],
                        "Strategy %": r.metrics["strategy_return"], "Buy & hold %": r.metrics["buy_hold_return"]}
                       for r in results]
        print(f"✅ {model.name}: direction {stats['Direction acc. %']:.1f}% (p={stats['Binomial p (vs 50%)']:.3f}), "
              f"skill {stats['Mean skill vs naive']:+.3f}, sig. better/worse {stats['Sig. better than naive']}/{stats['Sig. worse than naive']}")

    table = pd.DataFrame(rows)
    os.makedirs("results", exist_ok=True)
    table.to_csv("results/model_comparison.csv", index=False)
    pd.DataFrame(per_ticker).to_csv("results/model_comparison_per_ticker.csv", index=False)
    end = max(pd.Timestamp(df["timestamp"].iloc[-1]) for df in data.values())
    with open("results/model_comparison.md", "w", encoding="utf-8") as f:
        f.write(f"Walk-forward backtest: {len(data)} tickers × last {test_days} trading days (ending {end:%d %b %Y}), "
                f"models re-trained every 21 days on past data only, {COST_PER_TRADE:.1%} cost per trade. "
                f"Binomial test: is pooled direction accuracy > 50%?\n\n")
        f.write(to_markdown(table))
        f.write("\n")
    print("\n" + table.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    return table


def main(tickers=None):
    import os
    from database import get_all_monitored_tickers, fetch_unified_data

    tickers = tickers or get_all_monitored_tickers()
    results = []
    for t in tickers:
        try:
            r = run_backtest(t, fetch_unified_data(t))
            results.append(r)
            print(f"✅ {t}: {verdict(r.metrics)}")
        except Exception as e:
            print(f"⚠️ {t}: skipped ({e})")
    if not results:
        return

    table = summary_table(results)
    os.makedirs("results", exist_ok=True)
    table.to_csv("results/backtest_summary.csv", index=False)
    pooled_dir = np.mean([r.metrics["direction_accuracy"] for r in results])
    beaten = sum(r.metrics["skill_vs_naive"] > 0 and r.metrics["dm_p_value"] < 0.05 for r in results)
    m0 = results[0].metrics
    with open("results/backtest_summary.md", "w", encoding="utf-8") as f:
        from prediction_engine import PRODUCTION_MODEL_NAME
        f.write(f"Model: {PRODUCTION_MODEL_NAME}. Walk-forward backtest, {m0['test_days']} trading days per ticker "
                f"(ending {pd.Timestamp(m0['end']):%d %b %Y}), retrained every 21 days, "
                f"{COST_PER_TRADE:.1%} cost per trade.\n\n")
        f.write(to_markdown(table))
        f.write(f"\n\nModel significantly beats the naive forecast on {beaten}/{len(results)} tickers; "
                f"mean direction accuracy {pooled_dir:.1f}%.\n")
    print(f"\n📄 Saved results/backtest_summary.md and .csv")
    print(table.to_string(index=False, float_format=lambda x: f"{x:.2f}"))


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--compare" in args:
        compare_models([a for a in args if a != "--compare"] or None)
    else:
        main(args or None)
