import time
from hyperliquid.info import Info
from hyperliquid.utils import constants

info = Info(constants.TESTNET_API_URL, skip_ws=True)


def get_ohlcv(coin, interval):
    print(f"--- Fetching {interval} candles for {coin} ---")

    candles = info.candles_snapshot(coin, interval, 0, int(time.time() * 1000))

    if not candles:
        print("No data found.")
        return

    latest_candle = candles[-1]

    open_p = latest_candle["o"]
    high_p = latest_candle["h"]
    low_p = latest_candle["l"]
    close_p = latest_candle["c"]
    volume = latest_candle["v"]

    print(f"Open: {open_p} | High: {high_p} | Low: {low_p} | Close: {close_p}")
    return candles


if __name__ == "__main__":
    get_ohlcv("BTC", "1d")
