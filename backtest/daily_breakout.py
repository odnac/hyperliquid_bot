import pandas as pd
import time
from hyperliquid.info import Info
from hyperliquid.utils import constants

info = Info(constants.TESTNET_API_URL, skip_ws=True)


def run_backtest(coin, interval):
    # 1. Fetch historical candle data
    # snapshot fetches up to 5000 candles
    candles = info.candles_snapshot(coin, interval, 0, int(time.time() * 5000))
    df = pd.DataFrame(candles)

    # 2. Data Preprocessing
    # Convert Unix timestamp (ms) to readable KST timezone
    df["Time"] = (
        pd.to_datetime(df["t"], unit="ms")
        .dt.tz_localize("UTC")
        .dt.tz_convert("Asia/Seoul")
    )

    # Format date string for better readability
    df["Time"] = df["Time"].dt.strftime("%Y-%m-%d %H:%M")

    # Select necessary columns and convert to float
    df = df[["Time", "o", "h", "l", "c"]].copy()
    df.columns = ["Date", "Open", "High", "Low", "Close"]
    df[["Open", "High", "Low", "Close"]] = df[["Open", "High", "Low", "Close"]].astype(
        float
    )

    # 3. Strategy Logic: Daily High Breakout
    # Prev_High is the high price of the previous candle
    df["Prev_High"] = df["High"].shift(1)

    # Buy Signal: If current candle's High is greater than previous High
    df["Signal"] = df["High"] > df["Prev_High"]

    # 4. Performance Calculation
    df["Return"] = 1.0

    # Calculate daily return if signal is triggered
    # Logic: Close price / Entry price (Prev_High)
    df.loc[df["Signal"], "Return"] = df["Close"] / df["Prev_High"]

    # Cumulative return (compounding)
    df["Total_Return"] = df["Return"].cumprod()

    print(f"--- {coin} Backtest Result ({interval}) ---")
    print(df[["Date", "Prev_High", "High", "Close", "Total_Return"]].tail(10))
    print(f"\nFinal Cumulative Return: {df['Total_Return'].iloc[-1]:.4f}x")


if __name__ == "__main__":
    run_backtest("BTC", "1d")
