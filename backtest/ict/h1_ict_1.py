# h1_ict_1.py
import time
import pandas as pd
from hyperliquid.utils import constants
from hyperliquid.info import Info
import plotly.graph_objects as go

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


# =========================
# H1 POI
# =========================
def find_h1_pois(df):
    pois = []
    n = 24  # Tail search range and volatility reference range

    if len(df) < n + 5:
        return pois

    for i in range(n, len(df)):
        c1, c2, c3 = df.iloc[i - 2], df.iloc[i - 1], df.iloc[i]

        # --- [Common 1: Volatility Filter] ---
        prev_bodies = abs(
            df["close"].iloc[i - (n + 1) : i - 1] - df["open"].iloc[i - (n + 1) : i - 1]
        )
        avg_body_size = prev_bodies.mean()
        curr_body_size = abs(c2["close"] - c2["open"])
        if curr_body_size < (avg_body_size * 2.0):
            continue

        # --- [Common 2: check gap] ---
        is_long_gap = c3["low"] > c1["high"]
        is_short_gap = c3["high"] < c1["low"]
        if not (is_long_gap or is_short_gap):
            continue

        # --- [FVG (candle tail overlap)] ---
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
                    u_wick_t, u_wick_b = prev["high"], max(prev["open"], prev["close"])

                    top, bottom = min(fvg_t, u_wick_t), max(fvg_b, u_wick_b)
                    if top > bottom:
                        pois.append(
                            {
                                "side": "LONG",
                                "type": "FVG_Wick_Overlap",
                                "top": top,
                                "bottom": bottom,
                            }
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
                    l_wick_t, l_wick_b = min(prev["open"], prev["close"]), prev["low"]

                    top, bottom = min(fvg_t, l_wick_t), max(fvg_b, l_wick_b)
                    if top > bottom:
                        pois.append(
                            {
                                "side": "SHORT",
                                "type": "FVG_Wick_Overlap",
                                "top": top,
                                "bottom": bottom,
                            }
                        )
                        break

        # --- [OB] ---
        if is_long_gap:
            if (
                c1["close"] < c1["open"]
                and c2["close"] > c2["open"]
                and c3["close"] > c3["open"]
            ) or (
                c1["close"] > c1["open"]
                and c2["close"] > c2["open"]
                and c3["close"] < c3["open"]
            ):
                pois.append(
                    {
                        "side": "LONG",
                        "type": "OB_Pattern",
                        "top": c1["high"],
                        "bottom": c1["low"],
                    }
                )
        elif is_short_gap:
            if (
                c1["close"] > c1["open"]
                and c2["close"] < c2["open"]
                and c3["close"] < c3["open"]
            ) or (
                c1["close"] < c1["open"]
                and c2["close"] < c2["open"]
                and c3["close"] > c3["open"]
            ):
                pois.append(
                    {
                        "side": "SHORT",
                        "type": "OB_Pattern",
                        "top": c1["high"],
                        "bottom": c1["low"],
                    }
                )

    return pois


# =====================================================
# M5 Engulfing
# =====================================================
def check_m5_engulfing(df_m5):
    if len(df_m5) < 2:
        return None, None
    prev, curr = df_m5.iloc[-2], df_m5.iloc[-1]
    if (
        prev["close"] < prev["open"]
        and curr["close"] > curr["open"]
        and curr["close"] > prev["open"]
    ):
        return "LONG", curr["low"]
    if (
        prev["close"] > prev["open"]
        and curr["close"] < curr["open"]
        and curr["close"] < prev["open"]
    ):
        return "SHORT", curr["high"]
    return None, None


# =====================================================
# M1 CHoCH
# =====================================================
def check_m1_choch(df_m1, direction):
    if len(df_m1) < 5:
        return False, None
    if direction == "LONG":
        last_swing_high = df_m1["high"].iloc[-5:-1].max()
        if df_m1["close"].iloc[-1] > last_swing_high:
            return True, df_m1["low"].iloc[-3:].min()
    elif direction == "SHORT":
        last_swing_low = df_m1["low"].iloc[-5:-1].min()
        if df_m1["close"].iloc[-1] < last_swing_low:
            return True, df_m1["high"].iloc[-3:].max()
    return False, None


# =====================================================
# Backtest Visualize
# =====================================================
def visualize_backtest(df_h1, results):
    if not results:
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
            font=dict(color=color, size=20),
        )
        fig.add_shape(
            type="line",
            x0=trade["Date"],
            y0=trade["TP"],
            x1=trade["Date"] + pd.Timedelta(hours=10),
            y1=trade["TP"],
            line=dict(color="green", width=1, dash="dot"),
        )
        fig.add_shape(
            type="line",
            x0=trade["Date"],
            y0=trade["SL"],
            x1=trade["Date"] + pd.Timedelta(hours=10),
            y1=trade["SL"],
            line=dict(color="red", width=1, dash="dot"),
        )
    fig.update_layout(
        title=f"{SYMBOL} Backtest Result",
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
    )
    fig.write_html("backtest_chart_1.html")
    print("\n✅ Complete Visualization: 'backtest_chart_1.html' open file.")


def run_backtest_logic():
    print(f"⌛ Collecting Data..")
    df_h1 = get_ohlcv(SYMBOL, "1h", 15)
    df_m5 = get_ohlcv(SYMBOL, "5m", 15)
    df_m1 = get_ohlcv(SYMBOL, "1m", 15)
    if df_h1 is None or df_m5 is None:
        return

    print(f"🚀 Start Backtesting...")
    results = []
    used_poi_ids = set()
    total = len(df_m5)

    for i in range(50, total):
        if i % 500 == 0:
            print(f"⏳ Progress: {i}/{total} ({ (i/total)*100:.1f}%)")
        curr_time = df_m5.index[i]
        curr_price = df_m5["close"].iloc[i]
        lookback_h1 = df_h1[df_h1.index <= curr_time]
        pois = find_h1_pois(lookback_h1)
        for poi in pois:
            poi_id = f"{poi['side']}_{poi['top']:.1f}_{poi['bottom']:.1f}"
            if poi_id in used_poi_ids:
                continue
            if poi["bottom"] <= curr_price <= poi["top"]:
                lookback_m5 = df_m5[df_m5.index <= curr_time]
                signal, sl_price = check_m5_engulfing(lookback_m5)
                if not signal:
                    lookback_m1 = df_m1[df_m1.index <= curr_time]
                    is_choch, choch_sl = check_m1_choch(lookback_m1, poi["side"])
                    if is_choch:
                        signal, sl_price = poi["side"], choch_sl
                if signal == poi["side"]:
                    entry_price = curr_price
                    sl_dist = abs(entry_price - sl_price)
                    if sl_dist < 5:
                        continue
                    tp_price = (
                        entry_price + (sl_dist * RISK_REWARD_RATIO)
                        if signal == "LONG"
                        else entry_price - (sl_dist * RISK_REWARD_RATIO)
                    )
                    future_df = df_m5[df_m5.index > curr_time]
                    outcome = "OPEN"
                    for f_time, f_candle in future_df.iterrows():
                        if signal == "LONG":
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
                                "Side": signal,
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
