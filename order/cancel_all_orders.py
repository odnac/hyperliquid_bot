import os
import eth_account
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

COIN_NAME="BTC"

load_dotenv()
MY_ADDRESS = os.getenv("HYPER_TESTNET_ACCOUNT_ADDRESS")
API_KEY = os.getenv("HYPER_TESTNET_PRIVATE_KEY")
base_url = constants.TESTNET_API_URL

info = Info(base_url, skip_ws=True)
account = eth_account.Account.from_key(API_KEY)
exchange = Exchange(account, base_url, account_address=MY_ADDRESS)

def cancel_all_orders():
    print("--- Fetching Open Orders to Cancel ---")
    try:
        open_orders = info.open_orders(address=MY_ADDRESS)
        
        coin_orders = [o for o in open_orders if o['coin'] == COIN_NAME]
        
        if not coin_orders:
            print("No open BTC orders found to cancel.")
            return

        for order in coin_orders:
            oid = order['oid'] # Order ID
            print(f"Canceling Order ID: {oid}...")
            
            cancel_result = exchange.cancel(COIN_NAME, oid)
            
            if cancel_result["status"] == "ok":
                print(f"✅ Successfully canceled order {oid}")
            else:
                print(f"❌ Failed to cancel order {oid}: {cancel_result}")

    except Exception as e:
        print(f"Error during cancellation: {e}")

if __name__ == "__main__":
    cancel_all_orders()