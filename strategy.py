def simple_strategy(api):
    positions = api.list_positions()
    if not positions:
        api.submit_order(symbol="AAPL", qty=1, side="buy", type="market", time_in_force="gtc")
