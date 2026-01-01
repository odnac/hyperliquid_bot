import time
import pandas as pd
from hyperliquid.utils import constants
from hyperliquid.info import Info

# =====================================================
# Setting
# =====================================================
SYMBOL = "BTC"
BASE_URL = constants.TESTNET_API_URL
RISK_REWARD_RATIO = 3.0

info = Info(BASE_URL, skip_ws=True)


# =====================================================
# Data collection
# =====================================================
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


# =====================================================
# H1 Market Sturcture
# =====================================================
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


# =====================================================
# H1 POI (OB / Enhanced FVG)
# =====================================================
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

        # ---------- OB ----------
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

        # ---------- Enhanced FVG ----------
        if bulls == 3 and bull_gap:
            fvg_top, fvg_bot = c3["low"], c1["high"]
            for j in range(i - lookback, i - 2):
                p = df.iloc[j]
                if p["close"] < p["open"]:
                    wt, wb = p["high"], max(p["open"], p["close"])
                    top, bot = min(fvg_top, wt), max(fvg_bot, wb)
                    if top > bot:
                        pois.append(
                            {
                                "type": "FVG",
                                "side": "LONG",
                                "top": top,
                                "bottom": bot,
                                "created": df.index[i],
                            }
                        )
                        break

        if bears == 3 and bear_gap:
            fvg_top, fvg_bot = c1["low"], c3["high"]
            for j in range(i - lookback, i - 2):
                p = df.iloc[j]
                if p["close"] > p["open"]:
                    wt, wb = min(p["open"], p["close"]), p["low"]
                    top, bot = min(fvg_top, wt), max(fvg_bot, wb)
                    if top > bot:
                        pois.append(
                            {
                                "type": "FVG",
                                "side": "SHORT",
                                "top": top,
                                "bottom": bot,
                                "created": df.index[i],
                            }
                        )
                        break
    return pois


# =====================================================
# M1 CHoCH
# =====================================================
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


# =====================================================
# M5 Engulfing + Displacement
# =====================================================
def check_m5_engulfing(df, side, lookback=20, factor=1.5):
    if len(df) < lookback + 2:
        return False, None

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    body_prev = abs(prev["close"] - prev["open"])
    body_curr = abs(curr["close"] - curr["open"])
    avg_body = (df["close"].iloc[-lookback:] - df["open"].iloc[-lookback:]).abs().mean()

    if body_curr < avg_body * factor:
        return False, None

    # LONG
    if side == "LONG":
        if prev["close"] < prev["open"] and curr["close"] > curr["open"]:
            if curr["open"] <= prev["close"] and curr["close"] >= prev["open"]:
                return True, min(prev["low"], curr["low"])

    # SHORT
    if side == "SHORT":
        if prev["close"] > prev["open"] and curr["close"] < curr["open"]:
            if curr["open"] >= prev["close"] and curr["close"] <= prev["open"]:
                return True, max(prev["high"], curr["high"])

    return False, None


# =====================================================
# Backtest
# =====================================================
def run_backtest():
    df_h1 = get_ohlcv(SYMBOL, "1h", 90)
    df_m5 = get_ohlcv(SYMBOL, "5m", 90)
    df_m1 = get_ohlcv(SYMBOL, "1m", 90)

    if df_h1 is None or df_m5 is None or df_m1 is None:
        print("Data collection failed")
        return

    results = []
    used_pois = set()
    in_position = False

    for i in range(50, len(df_m5)):
        curr_time = df_m5.index[i]
        curr_price = df_m5["close"].iloc[i]

        if in_position:
            continue

        h1 = df_h1[df_h1.index <= curr_time]
        trend = get_h1_structure(h1)
        if trend == "NEUTRAL":
            continue

        pois = find_h1_pois(h1)

        for p in pois:
            if p["created"] > curr_time:
                continue
            if p["side"] != ("LONG" if trend == "BULLISH" else "SHORT"):
                continue

            pid = f"{p['type']}_{p['side']}_{p['created']}"
            if pid in used_pois:
                continue

            if not (p["bottom"] <= curr_price <= p["top"]):
                continue

            # ---- trigger ----
            m1 = df_m1[df_m1.index <= curr_time]
            choch_ok, sl_m1 = check_m1_choch(m1, p["side"])

            m5 = df_m5[df_m5.index <= curr_time].iloc[-25:]
            engulf_ok, sl_m5 = check_m5_engulfing(m5, p["side"])

            if not (choch_ok or engulf_ok):
                continue

            sl = sl_m1 if choch_ok else sl_m5
            risk = abs(curr_price - sl)
            if risk < 5:
                continue

            tp = (
                curr_price + risk * RISK_REWARD_RATIO
                if p["side"] == "LONG"
                else curr_price - risk * RISK_REWARD_RATIO
            )

            in_position = True

            # ---- Result Judgment ----
            outcome = "OPEN"
            for _, c in df_m5[df_m5.index > curr_time].iterrows():
                if p["side"] == "LONG":
                    if c["high"] >= tp:
                        outcome = "WIN"
                        break
                    if c["low"] <= sl:
                        outcome = "LOSE"
                        break
                else:
                    if c["low"] <= tp:
                        outcome = "WIN"
                        break
                    if c["high"] >= sl:
                        outcome = "LOSE"
                        break

            in_position = False

            if outcome != "OPEN":
                results.append(
                    {
                        "time": curr_time,
                        "side": p["side"],
                        "entry": curr_price,
                        "sl": sl,
                        "tp": tp,
                        "result": outcome,
                    }
                )
                used_pois.add(pid)
                break

    if results:
        df = pd.DataFrame(results)
        wins = (df["result"] == "WIN").sum()
        print(df)
        print(f"\ntotal trades {len(df)} | Win Rate {(wins/len(df))*100:.2f}%")
    else:
        print("No deals matching the criteria")


# =====================================================
if __name__ == "__main__":
    run_backtest()
