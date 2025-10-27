import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime
from strategy import calculate_indicators, decide_and_size

# --- Aktienauswahl ---
STOCKS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]

# --- Zeitraum ---
START_DATE = "2023-01-01"
END_DATE = datetime.now().strftime("%Y-%m-%d")

# --- Kapital & Kosten ---
INITIAL_BALANCE = 10000
TRANSACTION_COST = 0.001  # 0.1%


def load_data(symbol):
    print(f"\n🔍 Lade Daten für {symbol} ...")
    df = yf.download(symbol, start=START_DATE, end=END_DATE, auto_adjust=False)

    # MultiIndex fix
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.columns = [str(c).lower() for c in df.columns]

    # Nur benötigte Spalten
    df = df[["open", "high", "low", "close"]].copy()
    df.dropna(inplace=True)

    return df


def backtest_strategy(symbol):
    df = load_data(symbol)
    df = calculate_indicators(df)

    balance = INITIAL_BALANCE
    position = 0
    entry_price = 0
    trades = []
    equity_curve = []

    for i in range(len(df)):
        latest = df.iloc[i]
        signal = decide_and_size(latest, balance)
        price = latest["close"]

        # Kauf
        if signal["action"] == "buy" and position == 0:
            cost = signal["qty"] * price * (1 + TRANSACTION_COST)
            if balance >= cost:
                balance -= cost
                position = signal["qty"]
                entry_price = price
                trades.append(("BUY", price, latest.name, signal["reason"]))

        # Verkauf
        elif signal["action"] == "sell" and position > 0:
            revenue = position * price * (1 - TRANSACTION_COST)
            pnl = (price - entry_price) * position
            balance += revenue
            trades.append(("SELL", price, latest.name, pnl, signal["reason"]))
            position = 0

        total_value = balance + (position * price if position > 0 else 0)
        equity_curve.append(total_value)

    # --- Automatisches Schließen am Ende ---
    if position > 0:
        final_price = df["close"].iloc[-1]
        revenue = position * final_price * (1 - TRANSACTION_COST)
        pnl = (final_price - entry_price) * position
        balance += revenue
        trades.append(("CLOSE_END", final_price, df.index[-1], pnl, "Auto-Close"))
        position = 0

    df["equity"] = equity_curve

    pnl = balance - INITIAL_BALANCE
    pct_return = (pnl / INITIAL_BALANCE) * 100
    max_drawdown = (df["equity"].cummax() - df["equity"]).max()
    max_drawdown_pct = (max_drawdown / df["equity"].cummax().max()) * 100

    print(f"{symbol}: {len(trades)} Trades ausgeführt.")
    return {
        "symbol": symbol,
        "trades": trades,
        "final_balance": balance,
        "total_return": pct_return,
        "max_drawdown": max_drawdown_pct,
        "equity": df["equity"],
    }


def run_backtest():
    results = []
    plt.figure(figsize=(10, 6))

    for stock in STOCKS:
        result = backtest_strategy(stock)
        results.append(result)
        plt.plot(result["equity"], label=stock)

    plt.title("💹 Portfolio-Entwicklung (Backtest 2023–2025)")
    plt.xlabel("Zeit")
    plt.ylabel("Kontostand (USD)")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.show()

    print("\n📊 Zusammenfassung:")
    for r in results:
        print(f"{r['symbol']}: {r['total_return']:.2f}% Rendite, "
              f"Max. Drawdown {r['max_drawdown']:.2f}%, "
              f"Endsaldo: {r['final_balance']:.2f} USD")


if __name__ == "__main__":
    run_backtest()
