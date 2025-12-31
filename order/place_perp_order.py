import os
import eth_account
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants


load_dotenv()
MY_ADDRESS = os.getenv("HYPER_TESTNET_ACCOUNT_ADDRESS")
API_KEY = os.getenv("HYPER_TESTNET_PRIVATE_KEY")

BASE_URL = constants.TESTNET_API_URL
LEVERAGE=10
COIN_NAME="BTC"
CROSS=True
ISOLATED=False

info = Info(base_url=BASE_URL, skip_ws=True)

account = eth_account.Account.from_key(API_KEY)
exchange = Exchange(account, base_url=BASE_URL, account_address=MY_ADDRESS)

def place_perp_order():
    try:
        print("Setting leverage to 10x...")
        exchange.update_leverage(leverage=LEVERAGE, name=COIN_NAME, is_cross=ISOLATED)
        
        all_mids = info.all_mids()
        btc_price = float(all_mids.get("BTC"))
        
        target_price = int(btc_price * 0.9) 
        quantity = 0.01
        
        print(f"Current BTC: ${btc_price}")
        print(f"Targeting Buy at: ${target_price}")

        order_result = exchange.order("BTC", True, quantity, target_price, {"limit": {"tif": "Gtc"}})
        
        print(f"Order Result: {order_result}")

        if order_result["status"] == "ok":
            status = order_result["response"]["data"]["statuses"][0]
            if "resting" in status:
                print("✅ Success! Your order is now on the book.")
            else:
                print(f"❌ Order Rejected: {status}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    place_perp_order()