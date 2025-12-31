import os
import eth_account
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

load_dotenv()
MY_ADDRESS = os.getenv("HYPER_TESTNET_ACCOUNT_ADDRESS")
API_KEY = os.getenv("HYPER_TESTNET_PRIVATE_KEY")

# --- Spot Settings ---
BASE_URL = constants.TESTNET_API_URL
SPOT_COIN = "HYPE/USDC"  # spot /USDC
PERCENT_TO_USE = 0.1  # 10%
BUY = True

info = Info(base_url=BASE_URL, skip_ws=True)
account = eth_account.Account.from_key(API_KEY)
exchange = Exchange(account, base_url=BASE_URL, account_address=MY_ADDRESS)


def get_spot_balance():
    user_state = info.user_state(MY_ADDRESS)
    return float(user_state["withdrawable"])


def place_spot_order():
    try:
        balance = get_spot_balance()
        all_mids = info.all_mids()
        coin_price = float(all_mids.get(SPOT_COIN))

        order_value = balance * PERCENT_TO_USE
        quantity = round(order_value / coin_price, 2)

        limit_price = round(coin_price * 0.99, 4)

        print(f"--- Spot Order: {SPOT_COIN} ---")
        print(f"Balance: {balance:.2f} USDC | Order Value: {order_value:.2f} USDC")
        print(f"Price: {limit_price} | Quantity: {quantity}")

        order_result = exchange.order(
            name=SPOT_COIN,
            is_buy=BUY,
            sz=quantity,
            limit_px=limit_price,
            order_type={"limit": {"tif": "Gtc"}},
        )

        if order_result["status"] == "ok":
            print("✅ Spot Order Success!")
        else:
            print(f"❌ Spot Order Failed: {order_result}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    place_spot_order()
