import os
import time
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.utils import constants

load_dotenv()
info = Info(constants.TESTNET_API_URL, skip_ws=True)

TARGET_PRICE = 95000.0 

def price_alert_bot():
    print(f"--- Monitoring BTC price. Alert at: ${TARGET_PRICE} ---")
    
    try:
        while True:
            all_mids = info.all_mids()
            current_price = float(all_mids.get("BTC", 0))

            if current_price >= TARGET_PRICE:
                print(f"🚨🚨 [ALERT] BTC hit ${current_price}! Target ${TARGET_PRICE} reached! 🚨🚨")
            else:
                print(f"Current Price: ${current_price} (Target: ${TARGET_PRICE})")

            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nStop monitoring.")

if __name__ == "__main__":
    price_alert_bot()