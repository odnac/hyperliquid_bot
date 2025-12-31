import os
import time
import eth_account
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

load_dotenv()
MY_ADDRESS = os.getenv("HYPER_TESTNET_ACCOUNT_ADDRESS")
API_KEY = os.getenv("HYPER_TESTNET_PRIVATE_KEY")
BASE_URL = constants.TESTNET_API_URL

info = Info(BASE_URL, skip_ws=True)
account = eth_account.Account.from_key(API_KEY)
exchange = Exchange(account, BASE_URL, account_address=MY_ADDRESS)

# --- 전략 설정 ---
COIN_NAME = "BTC"
TIMEFRAME = "1d"
PERCENT_TO_USE = 0.1
LEVERAGE = 10


def get_breakout_target():

    candles = info.candles_snapshot(COIN_NAME, TIMEFRAME, 0, int(time.time() * 1000))

    if len(candles) < 2:
        return None

    yesterday = candles[-2]
    yesterday_high = float(yesterday["h"])

    print(f"Yesterday's High: ${yesterday_high}")
    return yesterday_high


def run_strategy():
    try:
        target_price = get_breakout_target()
        if not target_price:
            return

        exchange.update_leverage(LEVERAGE, COIN_NAME, is_cross=False)

        print(f"🚀 Strategy Started. Target: Above ${target_price}")

        while True:
            all_mids = info.all_mids()
            current_price = float(all_mids.get(COIN_NAME))

            print(
                f"Current {COIN_NAME}: ${current_price} | Target: ${target_price}",
                end="\r",
            )

            if current_price > target_price:
                print(
                    f"\n✨ Breakout Detected! Price ${current_price} > Target ${target_price}"
                )

                user_state = info.user_state(MY_ADDRESS)
                balance = float(user_state["withdrawable"])

                order_value = balance * PERCENT_TO_USE * LEVERAGE
                quantity = round(order_value / current_price, 4)

                limit_px = int(current_price * 1.001)

                print(f"Placing Order: {quantity} {COIN_NAME}...")

                order_result = exchange.order(
                    name=COIN_NAME,
                    is_buy=True,
                    sz=quantity,
                    limit_px=limit_px,
                    order_type={"limit": {"tif": "Ioc"}},
                )

                if order_result["status"] == "ok":
                    print("✅ Entry Success! Breaking out of loop.")
                    break
                else:
                    print(f"❌ Entry Failed: {order_result}")

            time.sleep(10)

    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    run_strategy()
