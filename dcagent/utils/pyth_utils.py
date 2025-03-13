import json
import logging
import requests
from typing import Optional, Tuple

from web3 import Web3

from dcagent.config import PYTH_BTC_PRICE_FEED
from dcagent.utils.blockchain import web3

logger = logging.getLogger(__name__)

# Pyth Price Feed ABI (simplified for the necessary functions)
PYTH_PRICE_FEED_ABI = json.loads('''
[
    {
        "inputs": [
            {
                "internalType": "bytes32",
                "name": "id",
                "type": "bytes32"
            }
        ],
        "name": "getPriceUnsafe",
        "outputs": [
            {
                "components": [
                    {
                        "internalType": "int64",
                        "name": "price",
                        "type": "int64"
                    },
                    {
                        "internalType": "uint64",
                        "name": "conf",
                        "type": "uint64"
                    },
                    {
                        "internalType": "int32",
                        "name": "expo",
                        "type": "int32"
                    },
                    {
                        "internalType": "uint256",
                        "name": "publishTime",
                        "type": "uint256"
                    }
                ],
                "internalType": "struct PythStructs.Price",
                "name": "price",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]
''')

# The Pyth contract address on Base (this would be the mainnet or testnet pyth contract)
PYTH_CONTRACT_ADDRESS = "0x2880dC247b3c3b05a464fB03Bf2310A39FC1F05A"  # Base Mainnet Pyth contract

# Coinbase API endpoint for BTC price
COINBASE_BTC_PRICE_URL = "https://api.coinbase.com/v2/prices/BTC-USD/spot"

def get_btc_price_from_coinbase() -> Optional[float]:
    """
    Get the current BTC/USD price from Coinbase API
    
    Returns:
        float: The current BTC price in USD, or None if there was an error
    """
    try:
        response = requests.get(COINBASE_BTC_PRICE_URL, timeout=5)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        
        data = response.json()
        price_str = data.get('data', {}).get('amount')
        
        if not price_str:
            logger.error(f"No price data in Coinbase response: {data}")
            return None
            
        return float(price_str)
    except Exception as e:
        logger.error(f"Error fetching BTC price from Coinbase: {e}")
        return None

def get_btc_price_from_pyth() -> Optional[float]:
    """
    Get the current BTC/USD price from Pyth on-chain
    
    Returns:
        float: The current BTC price in USD, or None if there was an error
    """
    try:
        pyth_contract = web3.eth.contract(
            address=Web3.to_checksum_address(PYTH_CONTRACT_ADDRESS),
            abi=PYTH_PRICE_FEED_ABI
        )
        
        # Call the price feed to get latest BTC/USD price
        price_data = pyth_contract.functions.getPriceUnsafe(PYTH_BTC_PRICE_FEED).call()
        
        # Extract and format the price
        price = price_data[0]  # price field
        expo = price_data[2]   # exponent field
        
        # Pyth prices are stored as fixed-point numbers, need to adjust by exponent
        # The exponent is typically negative, like -8 for BTC/USD
        adjusted_price = price * (10 ** expo)
        
        return float(adjusted_price)
        
    except Exception as e:
        logger.error(f"Error fetching BTC price from Pyth: {e}")
        return None

def get_btc_price() -> Optional[float]:
    """
    Get the current BTC/USD price, trying Coinbase first, then Pyth as fallback
    
    Returns:
        float: The current BTC price in USD, or None if both sources failed
    """
    # Try Coinbase first
    price = get_btc_price_from_coinbase()
    if price is not None:
        logger.info(f"Got BTC price from Coinbase: ${price:,.2f}")
        return price
        
    # Fall back to Pyth if Coinbase fails
    logger.warning("Failed to get price from Coinbase, trying Pyth...")
    price = get_btc_price_from_pyth()
    if price is not None:
        logger.info(f"Got BTC price from Pyth: ${price:,.2f}")
        return price
        
    # Both sources failed
    logger.error("Failed to get BTC price from both Coinbase and Pyth")
    return None

def get_price_with_confidence() -> Optional[Tuple[float, float]]:
    """
    Get the current BTC/USD price and confidence interval
    
    Returns:
        Tuple[float, float]: The current BTC price in USD and confidence, or None if there was an error
    """
    # First try to get price from Coinbase
    price = get_btc_price_from_coinbase()
    if price is not None:
        # For Coinbase, we don't have a confidence interval, so use a default
        # Let's use 0.5% as a reasonable confidence value
        confidence = price * 0.005
        return (price, confidence)
    
    # Fall back to Pyth which provides confidence
    try:
        pyth_contract = web3.eth.contract(
            address=Web3.to_checksum_address(PYTH_CONTRACT_ADDRESS), 
            abi=PYTH_PRICE_FEED_ABI
        )
        
        # Call the price feed to get latest BTC/USD price
        price_data = pyth_contract.functions.getPriceUnsafe(PYTH_BTC_PRICE_FEED).call()
        
        # Extract price components
        price = price_data[0]  # price field
        conf = price_data[1]   # confidence field
        expo = price_data[2]   # exponent field
        
        # Pyth prices are stored as fixed-point numbers, need to adjust by exponent
        adjusted_price = price * (10 ** expo)
        adjusted_conf = conf * (10 ** expo)
        
        return (float(adjusted_price), float(adjusted_conf))
        
    except Exception as e:
        logger.error(f"Error fetching BTC price with confidence: {e}")
        return None