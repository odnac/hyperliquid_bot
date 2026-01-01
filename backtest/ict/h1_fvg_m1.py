import time
import pandas as pd
from hyperliquid.utils import constants
from hyperliquid.info import Info

# =========================
# Setting
# =========================
SYMBOL = "BTC"
BASE_URL = constants.TESTNET_API_URL
RISK_REWARD_RATIO = 3.0

info = Info(BASE_URL, skip_ws=True)


# =========================
# Data collection
# =========================
def get_ohlcv(symbol, interval, days=15):
    start = int((time.time() - 86400 * days) * 1000)
    end = int(time.time() * 1000)
    candles = info.candles_snapshot(symbol, interval, start, end)
    if not candles:
        return None

    df = pd.DataFrame(candles)
    df = df.rename(
        columns={"t": "timestamp", "o": "open", "h": "high", "l": "low", "c": "close"}
    )
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(
        float
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df


# =========================
# H1 Market Sturcture
# =========================
def find_swings(df, left=2, right=2):
    highs, lows = [], []
    for i in range(left, len(df) - right):
        if df["high"].iloc[i] == df["high"].iloc[i - left : i + right + 1].max():
            highs.append((df.index[i], df["high"].iloc[i]))
        if df["low"].iloc[i] == df["low"].iloc[i - left : i + right + 1].min():
            lows.append((df.index[i], df["low"].iloc[i]))
    return highs, lows


def filter_swings(swings, min_dist=0.003):
    out = []
    for t, p in swings:
        if not out or abs(p - out[-1][1]) / out[-1][1] > min_dist:
            out.append((t, p))
    return out


def get_h1_structure(df):
    highs, lows = find_swings(df)
    highs = filter_swings(highs)
    lows = filter_swings(lows)

    if len(highs) < 2 or len(lows) < 2:
        return "NEUTRAL"

    lh, ph = highs[-1][1], highs[-2][1]
    ll, pl = lows[-1][1], lows[-2][1]
    close = df["close"].iloc[-1]

    if lh > ph and ll > pl and close > lh:
        return "BULLISH"
    if ll < pl and lh < ph and close < ll:
        return "BEARISH"

    return "NEUTRAL"


# =========================
# H1 POI
# =========================
def is_displacement(c, prev, factor=2.0):
    bodies = (prev["close"] - prev["open"]).abs()
    return abs(c["close"] - c["open"]) >= bodies.mean() * factor


def find_h1_pois(df):
    pois = []
    lookback = 30

    for i in range(lookback, len(df)):
        c1, c2, c3 = df.iloc[i - 2], df.iloc[i - 1], df.iloc[i]
        prev = df.iloc[i - lookback : i - 1]

        if not is_displacement(c2, prev):
            continue

        bull_gap = c3["low"] > c1["high"]
        bear_gap = c3["high"] < c1["low"]
        if not (bull_gap or bear_gap):
            continue

        colors = [
            c1["close"] > c1["open"],
            c2["close"] > c2["open"],
            c3["close"] > c3["open"],
        ]
        bulls = sum(colors)
        bears = 3 - bulls

        if bulls == 2 or bears == 2:
            pois.append(
                {
                    "type": "OB",
                    "side": "LONG" if bulls == 2 else "SHORT",
                    "top": c1["high"],
                    "bottom": c1["low"],
                    "created": df.index[i],
                }
            )
            continue

    return pois


# =========================
# M1 CHoCH
# =========================
def check_m1_choch(df, side):
    if len(df) < 15:
        return False, None

    if side == "LONG":
        swing = df["high"].iloc[-10:-1].max()
        if df["close"].iloc[-1] > swing:
            return True, df["low"].iloc[-5:].min()
    else:
        swing = df["low"].iloc[-10:-1].min()
        if df["close"].iloc[-1] < swing:
            return True, df["high"].iloc[-5:].max()

    return False, None


# =========================
# Backtest
# =========================
def run_backtest():
    df_h1 = get_ohlcv(SYMBOL, "1h", 90)
    df_m5 = get_ohlcv(SYMBOL, "5m", 90)
    df_m1 = get_ohlcv(SYMBOL, "1m", 90)

    if df_h1 is None:
        return

    results = []
    used = set()
    in_position = False

    for i in range(50, len(df_m5)):
        t = df_m5.index[i]
        price = df_m5["close"].iloc[i]

        if in_position:
            continue

        h1 = df_h1[df_h1.index <= t]
        trend = get_h1_structure(h1)
        if trend == "NEUTRAL":
            continue

        pois = find_h1_pois(h1)

        for p in pois:
            if p["created"] > t:
                continue
            if p["side"] != ("LONG" if trend == "BULLISH" else "SHORT"):
                continue

            pid = f"{p['type']}_{p['side']}_{p['created']}"
            if pid in used:
                continue

            if not (p["bottom"] <= price <= p["top"]):
                continue

            m1 = df_m1[df_m1.index <= t]
            ok, sl = check_m1_choch(m1, p["side"])
            if not ok:
                continue

            dist = abs(price - sl)
            if dist < 5:
                continue

            tp = (
                price + dist * RISK_REWARD_RATIO
                if p["side"] == "LONG"
                else price - dist * RISK_REWARD_RATIO
            )

            future = df_m5[df_m5.index > t]
            result = "OPEN"

            in_position = True

            for _, c in future.iterrows():
                if p["side"] == "LONG":
                    if c["high"] >= tp:
                        result = "WIN"
                        break
                    if c["low"] <= sl:
                        result = "LOSE"
                        break
                else:
                    if c["low"] <= tp:
                        result = "WIN"
                        break
                    if c["high"] >= sl:
                        result = "LOSE"
                        break

            in_position = False

            if result != "OPEN":
                results.append(
                    {
                        "time": t,
                        "side": p["side"],
                        "entry": price,
                        "sl": sl,
                        "tp": tp,
                        "result": result,
                    }
                )
                used.add(pid)
                break

    if results:
        df = pd.DataFrame(results)
        wins = (df["result"] == "WIN").sum()
        print(df)
        print(f"\ntotal trades {len(df)} | Win Rate {(wins/len(df))*100:.2f}%")
    else:
        print("No deals matching the criteria")


# =========================
if __name__ == "__main__":
    run_backtest()
