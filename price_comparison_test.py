#!/usr/bin/env python3
# price_comparison_test.py - Test script to compare Coinbase and Pyth prices

import logging
import time
from dcagent.utils.pyth_utils import get_btc_price_from_coinbase, get_btc_price, get_price_with_confidence

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Run price comparison tests and log results"""
    print("DCAgent Price Source Comparison Test\n")
    
    # Test 1: Get price from Coinbase
    print("Test 1: Coinbase Price Feed")
    start_time = time.time()
    coinbase_price = get_btc_price_from_coinbase()
    coinbase_time = time.time() - start_time
    
    if coinbase_price:
        print(f"✅ Coinbase BTC/USD: ${coinbase_price:,.2f}")
        print(f"   Response time: {coinbase_time:.4f} seconds")
    else:
        print("❌ Failed to get price from Coinbase")
    
    # Test 2: Get price from combined function (with fallback)
    print("\nTest 2: Combined Price Feed (with fallback)")
    start_time = time.time()
    price = get_btc_price()
    combined_time = time.time() - start_time
    
    if price:
        print(f"✅ Combined BTC/USD: ${price:,.2f}")
        print(f"   Response time: {combined_time:.4f} seconds")
    else:
        print("❌ Failed to get price from all sources")
    
    # Test 3: Get price with confidence interval
    print("\nTest 3: Price with Confidence Interval")
    start_time = time.time()
    price_conf = get_price_with_confidence()
    conf_time = time.time() - start_time
    
    if price_conf:
        price, conf = price_conf
        print(f"✅ BTC/USD: ${price:,.2f} ± ${conf:,.2f}")
        print(f"   Confidence: {(conf/price)*100:.2f}%")
        print(f"   Response time: {conf_time:.4f} seconds")
    else:
        print("❌ Failed to get price with confidence")
    
    print("\nSummary:")
    print(f"- Coinbase API is {'available' if coinbase_price else 'unavailable'}")
    print(f"- Using Coinbase as primary price source for DCAgent")
    
if __name__ == "__main__":
    main()