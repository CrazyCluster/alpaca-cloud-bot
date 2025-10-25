import os
from flask import escape

def trade(request):
    token = request.headers.get("X-Invoke-Token")
    if not token or token != os.getenv("INVOKE_SECRET"):
        return ("Unauthorized", 401)

    from alpaca_trade_api.rest import REST

    api_key = os.getenv("ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_API_SECRET")
    base_url = "https://paper-api.alpaca.markets"

    api = REST(api_key, api_secret, base_url)

    positions = api.list_positions()
    print("Aktuelle Positionen:", positions)

    if not positions:
        api.submit_order(
            symbol="AAPL",
            qty=1,
            side="buy",
            type="market",
            time_in_force="gtc"
        )

    return ("Trade ausgeführt ✅", 200)
