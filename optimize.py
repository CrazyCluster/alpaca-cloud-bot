import optuna
import json
import numpy as np
import yfinance as yf
import pandas as pd
from datetime import datetime

# -----------------------------------
# Parameter
# -----------------------------------
START_DATE = "2023-01-01"
END_DATE = datetime.now().strftime("%Y-%m-%d")
STOCKS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]
INITIAL_BALANCE = 10000
TRANSACTION_COST = 0.001


# -----------------------------------
# Hilfsfunktionen
# -----------------------------------
def load_data(symbol):
    df = yf.download(symbol, start=START_DATE, end=END_DATE, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    df = df[["open", "high", "low", "close"]].copy()
    df.dropna(inplace=True)
    return df


def run_backtest(df, short_sma, long_sma, atr_period, risk_per_trade):
    df = df.copy()
    df["sma_short"] = df["close"].rolling(window=short_sma).mean()
    df["sma_long"] = df["close"].rolling(window=long_sma).mean()

    df["h-l"] = df["high"] - df["low"]
    df["h-c"] = abs(df["high"] - df["close"].shift())
    df["l-c"] = abs(df["low"] - df["close"].shift())
    df["tr"] = df[["h-l", "h-c", "l-c"]].max(axis=1)
    df["atr"] = df["tr"].rolling(window=atr_period).mean()
    df.dropna(inplace=True)

    balance = INITIAL_BALANCE
    position = 0
    entry_price = 0
    equity_curve = []

    for i in range(len(df)):
        latest = df.iloc[i]
        price = latest["close"]

        if latest["sma_short"] > latest["sma_long"] and position == 0:
            qty = max(int((balance * risk_per_trade) / latest["atr"]), 1)
            cost = qty * price * (1 + TRANSACTION_COST)
            if balance >= cost:
                balance -= cost
                position = qty
                entry_price = price

        elif latest["sma_short"] < latest["sma_long"] and position > 0:
            revenue = position * price * (1 - TRANSACTION_COST)
            balance += revenue
            position = 0

        total_value = balance + (position * price if position > 0 else 0)
        equity_curve.append(total_value)

    df["equity"] = equity_curve
    returns = pd.Series(df["equity"]).pct_change().dropna()

    if returns.std() == 0:
        return -999
    sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
    return sharpe_ratio


# -----------------------------------
# Optuna Objective über alle Aktien
# -----------------------------------
def objective(trial):
    short_sma = trial.suggest_int("SHORT_SMA", 5, 30)
    long_sma = trial.suggest_int("LONG_SMA", 40, 120)
    atr_period = trial.suggest_int("ATR_PERIOD", 5, 30)
    risk_per_trade = trial.suggest_float("RISK_PER_TRADE", 0.005, 0.05)

    sharpe_scores = []

    for stock in STOCKS:
        try:
            df = load_data(stock)
            score = run_backtest(df, short_sma, long_sma, atr_period, risk_per_trade)
            if score != -999:
                sharpe_scores.append(score)
        except Exception as e:
            print(f"⚠️ Fehler bei {stock}: {e}")

    if not sharpe_scores:
        return -999  # falls alles fehlschlägt

    # Durchschnittliche Sharpe Ratio aller Aktien
    avg_score = np.mean(sharpe_scores)
    return avg_score


# -----------------------------------
# Hauptteil
# -----------------------------------
if __name__ == "__main__":
    print("🚀 Starte Multi-Asset-Optimierung ...")
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=40)

    best_params = study.best_params
    print("\n🏆 Beste Parameterkombination (über alle 5 Aktien):")
    for k, v in best_params.items():
        print(f"{k}: {v}")

    print(f"\n📈 Durchschnittliche Sharpe Ratio: {study.best_value:.4f}")

    with open("best_params.json", "w") as f:
        json.dump(best_params, f, indent=4)
        print("\n💾 Gespeichert in best_params.json")
