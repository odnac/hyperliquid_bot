# h1_ict_2.py
import time
import pandas as pd
from hyperliquid.utils import constants
from hyperliquid.info import Info
import plotly.graph_objects as go

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
    try:
        start_time = int((time.time() - 86400 * days) * 1000)
        candles = info.candles_snapshot(
            symbol, interval, start_time, int(time.time() * 1000)
        )
        if not candles:
            return None

        df = pd.DataFrame(candles)
        df = df.rename(
            columns={
                "t": "timestamp",
                "o": "open",
                "h": "high",
                "l": "low",
                "c": "close",
            }
        )
        df[["open", "high", "low", "close"]] = df[
            ["open", "high", "low", "close"]
        ].astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df
    except Exception as e:
        print(f"Data Fetch Error ({interval}): {e}")
        return None


# =====================================================
# H1 Market Sturcture
# =====================================================
def check_h1_structure(df_h1):
    if len(df_h1) < 40:
        return "NEUTRAL"
    prev_high = df_h1["high"].iloc[-49:-1].max()  # -49:48
    prev_low = df_h1["low"].iloc[-49:-1].min()  # -49:48
    curr_close = df_h1["close"].iloc[-1]
    if curr_close > prev_high:
        return "BULLISH"
    if curr_close < prev_low:
        return "BEARISH"
    return "NEUTRAL"


# =====================================================
# H1 POI (FVG & OB)
# =====================================================
def find_h1_pois(df):
    pois = []
    n = 24

    if len(df) < n + 5:
        return pois

    for i in range(n, len(df)):
        c1, c2, c3 = df.iloc[i - 2], df.iloc[i - 1], df.iloc[i]
        prev_bodies = abs(
            df["close"].iloc[i - (n + 1) : i - 1] - df["open"].iloc[i - (n + 1) : i - 1]
        )
        avg_body = prev_bodies.mean()
        if abs(c2["close"] - c2["open"]) < (avg_body * 2.0):
            continue
        is_long_gap = c3["low"] > c1["high"]
        is_short_gap = c3["high"] < c1["low"]
        if not (is_long_gap or is_short_gap):
            continue

        if (
            is_long_gap
            and c1["close"] > c1["open"]
            and c2["close"] > c2["open"]
            and c3["close"] > c3["open"]
        ):
            fvg_t, fvg_b = c3["low"], c1["high"]
            for j in range(i - n, i - 2):
                prev = df.iloc[j]
                if prev["close"] < prev["open"]:
                    u_t, u_b = prev["high"], max(prev["open"], prev["close"])
                    top, bot = min(fvg_t, u_t), max(fvg_b, u_b)
                    if top > bot:
                        pois.append(
                            {"side": "LONG", "type": "FVG", "top": top, "bottom": bot}
                        )
                        break
        elif (
            is_short_gap
            and c1["close"] < c1["open"]
            and c2["close"] < c2["open"]
            and c3["close"] < c3["open"]
        ):
            fvg_t, fvg_b = c1["low"], c3["high"]
            for j in range(i - n, i - 2):
                prev = df.iloc[j]
                if prev["close"] > prev["open"]:
                    l_t, l_b = min(prev["open"], prev["close"]), prev["low"]
                    top, bot = min(fvg_t, l_t), max(fvg_b, l_b)
                    if top > bot:
                        pois.append(
                            {"side": "SHORT", "type": "FVG", "top": top, "bottom": bot}
                        )
                        break

        if is_long_gap and (
            (
                c1["close"] < c1["open"]
                and c2["close"] > c2["open"]
                and c3["close"] > c3["open"]
            )
            or (
                c1["close"] > c1["open"]
                and c2["close"] > c2["open"]
                and c3["close"] < c3["open"]
            )
        ):
            pois.append(
                {"side": "LONG", "type": "OB", "top": c1["high"], "bottom": c1["low"]}
            )
        elif is_short_gap and (
            (
                c1["close"] > c1["open"]
                and c2["close"] < c2["open"]
                and c3["close"] < c3["open"]
            )
            or (
                c1["close"] < c1["open"]
                and c2["close"] < c2["open"]
                and c3["close"] > c3["open"]
            )
        ):
            pois.append(
                {"side": "SHORT", "type": "OB", "top": c1["high"], "bottom": c1["low"]}
            )
    return pois


# =====================================================
# M1 CHoCH
# =====================================================
def check_m1_choch(df_m1, direction):
    if len(df_m1) < 15:
        return False, None
    if direction == "LONG":
        swing_high = df_m1["high"].iloc[-10:-1].max()
        if df_m1["close"].iloc[-1] > swing_high:
            return True, df_m1["low"].iloc[-5:].min()
    else:
        swing_low = df_m1["low"].iloc[-10:-1].min()
        if df_m1["close"].iloc[-1] < swing_low:
            return True, df_m1["high"].iloc[-5:].max()
    return False, None


# =====================================================
# Backtest Visualize
# =====================================================
def visualize_backtest(df_h1, results):
    if not results:
        print("There is no transaction data to visualize.")
        return
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df_h1.index,
                open=df_h1["open"],
                high=df_h1["high"],
                low=df_h1["low"],
                close=df_h1["close"],
                name="H1 Chart",
            )
        ]
    )

    for trade in results:
        color = "royalblue" if trade["Result"] == "WIN" else "indianred"
        fig.add_annotation(
            x=trade["Date"],
            y=trade["Entry"],
            text="▲" if trade["Side"] == "LONG" else "▼",
            showarrow=False,
            font=dict(color=color, size=18),
        )
        fig.add_shape(
            type="line",
            x0=trade["Date"],
            y0=trade["TP"],
            x1=trade["Date"] + pd.Timedelta(hours=6),
            y1=trade["TP"],
            line=dict(color="rgba(0, 255, 0, 0.5)", width=1, dash="dot"),
        )
        fig.add_shape(
            type="line",
            x0=trade["Date"],
            y0=trade["SL"],
            x1=trade["Date"] + pd.Timedelta(hours=6),
            y1=trade["SL"],
            line=dict(color="rgba(255, 0, 0, 0.5)", width=1, dash="dot"),
        )

    fig.update_layout(
        title=f"{SYMBOL} ICT Strategy Visual Backtest",
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
    )
    fig.write_html("backtest_chart_2.html")
    print("\n✅ Complete Visualization: 'backtest_chart_2.html' open file.")


def run_backtest_logic():
    print(f"⌛ Collecting Data..")
    df_h1, df_m5, df_m1 = (
        get_ohlcv(SYMBOL, "1h", 30),
        get_ohlcv(SYMBOL, "5m", 30),
        get_ohlcv(SYMBOL, "1m", 30),
    )
    if df_h1 is None or df_m5 is None or df_m1 is None:
        return

    print(f"🚀 Start Backtesting...")
    results, used_poi_ids = [], set()
    total = len(df_m5)

    for i in range(50, total):
        if i % 500 == 0:
            print(f"⏳ Progress: {i}/{total} ({(i/total)*100:.1f}%)")
        curr_time = df_m5.index[i]
        curr_price = df_m5["close"].iloc[i]

        lookback_h1 = df_h1[df_h1.index <= curr_time]
        h1_trend = check_h1_structure(lookback_h1)
        if h1_trend == "NEUTRAL":
            continue

        pois = find_h1_pois(lookback_h1)
        for poi in pois:
            if poi["side"] != ("LONG" if h1_trend == "BULLISH" else "SHORT"):
                continue
            poi_id = f"{poi['side']}_{poi['top']:.1f}_{poi['bottom']:.1f}"
            if poi_id in used_poi_ids:
                continue

            if poi["bottom"] <= curr_price <= poi["top"]:
                lookback_m1 = df_m1[df_m1.index <= curr_time]
                is_choch, sl_price = check_m1_choch(lookback_m1, poi["side"])

                if is_choch:
                    entry_price = curr_price
                    sl_dist = abs(entry_price - sl_price)
                    if sl_dist < 5:
                        continue
                    tp_price = (
                        entry_price + (sl_dist * RISK_REWARD_RATIO)
                        if poi["side"] == "LONG"
                        else entry_price - (sl_dist * RISK_REWARD_RATIO)
                    )

                    future_df = df_m5[df_m5.index > curr_time]
                    outcome = "OPEN"
                    for f_time, f_candle in future_df.iterrows():
                        if poi["side"] == "LONG":
                            if f_candle["high"] >= tp_price:
                                outcome = "WIN"
                                break
                            elif f_candle["low"] <= sl_price:
                                outcome = "LOSE"
                                break
                        else:
                            if f_candle["low"] <= tp_price:
                                outcome = "WIN"
                                break
                            elif f_candle["high"] >= sl_price:
                                outcome = "LOSE"
                                break

                    if outcome != "OPEN":
                        results.append(
                            {
                                "Date": curr_time,
                                "Side": poi["side"],
                                "Entry": entry_price,
                                "SL": sl_price,
                                "TP": tp_price,
                                "Result": outcome,
                            }
                        )
                        used_poi_ids.add(poi_id)
                        break

    if results:
        report = pd.DataFrame(results)
        print("\n" + report.to_string())
        win_c = (report["Result"] == "WIN").sum()
        print(
            f"\ntotal trades: {len(report)} | win: {win_c} | loss: {len(report)-win_c} | WinRate: {(win_c/len(report))*100:.2f}%"
        )
        visualize_backtest(df_h1, results)
    else:
        print("No deals matching the criteria")


if __name__ == "__main__":
    run_backtest_logic()
