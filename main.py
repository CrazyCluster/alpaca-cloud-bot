import os
from flask import Flask, request
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST, APIError
from strategy import decide_and_size

load_dotenv()
app = Flask(__name__)

SYMBOLS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]

@app.route("/", methods=["POST"])
def trade():
    token = request.headers.get("X-Invoke-Token")
    if token != os.getenv("INVOKE_SECRET"):
        return ("Unauthorized", 401)

    api = REST(
        os.getenv("ALPACA_API_KEY"),
        os.getenv("ALPACA_API_SECRET"),
        "https://paper-api.alpaca.markets"
    )

    results = []
    for symbol in SYMBOLS:
        try:
            print(f"🔍 Analysiere {symbol} ...")
            try:
                position = api.get_position(symbol)
            except APIError:
                position = None

            decision = decide_and_size(api, symbol)
            print(f"{symbol}: {decision}")

            if decision["action"] == "buy":
                if position:
                    results.append(f"{symbol}: Bereits in Position.")
                    continue
                api.submit_order(
                    symbol=symbol,
                    qty=decision["qty"],
                    side="buy",
                    type="market",
                    time_in_force="day",
                    order_class="bracket",
                    take_profit={"limit_price": decision["take_profit"]},
                    stop_loss={"stop_price": decision["stop_price"]}
                )
                results.append(f"{symbol}: Buy-Order platziert ✅")

            elif decision["action"] == "sell":
                if position:
                    api.submit_order(
                        symbol=symbol,
                        qty=position.qty,
                        side="sell",
                        type="market",
                        time_in_force="day"
                    )
                    results.append(f"{symbol}: Position geschlossen ✅")
                else:
                    results.append(f"{symbol}: Kein Bestand zum Verkaufen.")

            else:
                results.append(f"{symbol}: Kein Signal ({decision.get('reason')})")

        except Exception as e:
            print(f"Fehler bei {symbol}: {e}")
            results.append(f"{symbol}: Fehler → {e}")

    return {"results": results}, 200


if __name__ == "__main__":
    # 🔥 Lokaler Server, z. B. http://127.0.0.1:5000/
    app.run(host="0.0.0.0", port=5000)
