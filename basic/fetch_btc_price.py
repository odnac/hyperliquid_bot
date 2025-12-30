import os
import time
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.utils import constants

# Load environment variables
load_dotenv()

# Initialize Info object for Testnet
# No Private Key required for fetching public market data
info = Info(constants.TESTNET_API_URL, skip_ws=True)

def fetch_btc_price():
    print("Starting BTC price monitor... (Press Ctrl+C to stop)")
    try:
        while True:
            # Fetch all mid prices from the exchange
            all_mids = info.all_mids()
            
            # Extract BTC price
            btc_price = all_mids.get("BTC")
            
            if btc_price:
                print(f"Current BTC Price: {float(btc_price):.2f} USDC")
            else:
                print("BTC price data not found.")
            
            # Wait for 1 second before next update
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    fetch_btc_price()
    