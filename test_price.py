#!/usr/bin/env python3
# test_price.py - Test script for BTC price fetching functionality

import logging
from dcagent.utils.pyth_utils import get_btc_price, get_btc_price_from_coinbase, get_btc_price_from_pyth

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Test the price functions
print("Testing BTC price fetching...\n")

# Test Coinbase API
coinbase_price = get_btc_price_from_coinbase()
print(f"BTC price from Coinbase: ${coinbase_price:,.2f}" if coinbase_price else "Failed to get price from Coinbase")

# Test Pyth Oracle
pyth_price = get_btc_price_from_pyth()
print(f"BTC price from Pyth: ${pyth_price:,.2f}" if pyth_price else "Failed to get price from Pyth")

# Test combined function with fallback
btc_price = get_btc_price()
print(f"\nFinal BTC price with fallback: ${btc_price:,.2f}" if btc_price else "Failed to get BTC price from all sources")