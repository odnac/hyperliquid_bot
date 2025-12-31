import os
import eth_account
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

load_dotenv()
MY_ADDRESS = os.getenv("HYPER_TESTNET_ACCOUNT_ADDRESS")
API_KEY = os.getenv("HYPER_TESTNET_PRIVATE_KEY")

# --- Settings ---
BASE_URL = constants.TESTNET_API_URL
COIN_NAME = "BTC"
LEVERAGE = 10
PERCENT_TO_USE = 0.1  # (0.1 = 10%)
LONG = True
SHORT = False
CROSS = True
ISOLATED = False

info = Info(base_url=BASE_URL, skip_ws=True)
account = eth_account.Account.from_key(API_KEY)
exchange = Exchange(account, base_url=BASE_URL, account_address=MY_ADDRESS)


def get_withdrawable_balance():
    user_state = info.user_state(MY_ADDRESS)
    balance = float(user_state["withdrawable"])
    return balance


def place_perp_order():
    try:
        exchange.update_leverage(leverage=LEVERAGE, name=COIN_NAME, is_cross=ISOLATED)

        balance = get_withdrawable_balance()
        print(f"Current Balance: {balance:.2f} USDC")

        all_mids = info.all_mids()
        coin_price = float(all_mids.get(COIN_NAME))

        order_value = balance * PERCENT_TO_USE * LEVERAGE
        quantity = round(order_value / coin_price, 4)

        limit_price = int(coin_price * 0.99)

        if quantity <= 0:
            print("❌ Calculated quantity is too small.")
            return

        print(f"Targeting: {PERCENT_TO_USE*100}% of balance with {LEVERAGE}x leverage")
        print(f"Order Details: Buying {quantity} {COIN_NAME} at ${limit_price}")

        order_result = exchange.order(
            name=COIN_NAME,
            is_buy=LONG,
            sz=quantity,
            limit_px=limit_price,
            order_type={"limit": {"tif": "Gtc"}},
        )

        if order_result["status"] == "ok":
            print("✅ Order successfully placed!")
        else:
            print(f"❌ Order failed: {order_result}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    place_perp_order()
