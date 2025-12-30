# check_balance.py
import os
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.utils import constants

# Load .env file
load_dotenv()

# Get configuration values
MY_ADDRESS = os.getenv("HYPER_TESTNET_ACCOUNT_ADDRESS")
base_url = constants.TESTNET_API_URL

# Create Info object for data retrieval
info = Info(base_url, skip_ws=True)

def check_testnet_balance():
    try:
        # Retrieve user account state
        user_state = info.user_state(MY_ADDRESS)
        
        # Extract balance information from marginSummary
        margin_summary = user_state.get('marginSummary', {})
        
        # Balance items (default to '0' if data is missing)
        account_value = margin_summary.get('accountValue', '0')
        withdrawable = margin_summary.get('withdrawableIv', '0')
        
        print(f"--- [Hyperliquid Testnet Balance] ---")
        print(f"Wallet Address: {MY_ADDRESS}")
        print(f"Total Account Value: {float(account_value):.2f} USDC")
        print(f"Withdrawable Balance: {float(withdrawable):.2f} USDC")
        
    except Exception as e:
        print(f"Error during balance retrieval: {e}")
        # Uncomment the line below to see the full response structure for debugging
        print(user_state)

if __name__ == "__main__":
    check_testnet_balance()