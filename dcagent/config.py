import os
from dotenv import load_dotenv
from typing import Literal

# Load environment variables
load_dotenv()

# Network Configuration
BASE_RPC_URL = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
BASE_CHAIN_ID = int(os.getenv("BASE_CHAIN_ID", "8453"))

# Token Configuration
CBBTC_CONTRACT_ADDRESS = "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf"  # Base Mainnet cbBTC address
USDC_CONTRACT_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # Base Mainnet USDC address

# Pyth Price Feed Configuration
PYTH_BTC_PRICE_FEED = "0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43"  # BTC/USD price feed ID

# Agent Configuration
DCA_AMOUNT = float(os.getenv("DCA_AMOUNT", "50"))  # Default $50
DCA_INTERVAL: Literal["daily", "weekly", "monthly"] = os.getenv("DCA_INTERVAL", "weekly")  # type: ignore
ENABLE_DIP_BUYING = os.getenv("ENABLE_DIP_BUYING", "true").lower() == "true"
DIP_THRESHOLD = float(os.getenv("DIP_THRESHOLD", "5"))  # Default 5%

# Wallet Configuration
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

def validate_config() -> bool:
    """Validate that all required configuration is present"""
    required_vars = [
        "BASE_RPC_URL",
        "PRIVATE_KEY",
    ]
    
    for var in required_vars:
        if not globals().get(var):
            print(f"Missing required configuration: {var}")
            return False
    
    return True