Walk-forward backtest: 13 tickers × last 252 trading days (ending 30 Oct 2026), models re-trained every 21 days on past data only, 0.1% cost per trade. Binomial test: is pooled direction accuracy > 50%?

| Model | Tickers | Predictions | Mean skill vs naive | Sig. better than naive | Sig. worse than naive | Direction acc. % | Binomial p (vs 50%) | Mean strategy return % | Mean buy & hold % | Mean strategy Sharpe | Mean B&H Sharpe | Beat B&H (tickers) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Random Forest on prices (V2) | 13 | 3214 | -1.10 | 0 | 13 | 49.75 | 0.62 | -0.07 | 3.50 | 0.13 | 0.23 | 5 |
| Ridge regression on returns | 13 | 3214 | -0.02 | 0 | 6 | 49.75 | 0.62 | 0.29 | 3.50 | 0.01 | 0.23 | 7 |
| Gradient boosting on returns | 13 | 3214 | -0.05 | 0 | 5 | 49.25 | 0.81 | -3.16 | 3.50 | -0.39 | 0.23 | 6 |
| Gradient boosting on returns + sentiment | 13 | 3214 | -0.04 | 0 | 5 | 49.28 | 0.80 | -3.52 | 3.50 | -0.41 | 0.23 | 6 |
