#!/usr/bin/env python3
"""
Demo script to showcase Claude AI integration for DCAgent
"""

import logging
import json
import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Import after logging setup to capture all logs
from dcagent.utils.claude_advisor import ClaudeAdvisor
from dcagent.utils.pyth_utils import get_btc_price

def main():
    """Demo script to show Claude AI integration"""
    
    # Initialize Claude Advisor
    print("\n🤖 Initializing Claude AI Advisor...")
    advisor = ClaudeAdvisor()
    
    # Get current BTC price
    print("\n📊 Getting current BTC price...")
    btc_price = get_btc_price()
    print(f"Current BTC price: ${btc_price:,.2f}")
    
    # Create some simulated price history
    price_history = [
        btc_price * (1 + ((i - 10) * 0.005)) 
        for i in range(20)
    ]
    
    # Get market analysis
    print("\n🧠 Getting AI market analysis...")
    analysis = advisor.market_analysis(btc_price, price_history)
    print(f"\nMarket sentiment: {analysis['sentiment']}")
    print(f"Good buying opportunity: {analysis['buy_opportunity']}")
    print(f"Slippage recommendation: {analysis['slippage_recommendation']}%")
    print(f"Strategy recommendation: {analysis['strategy_recommendation']}")
    print(f"Reasoning: {analysis['reasoning']}")
    
    # Get transaction optimization
    print("\n⚙️ Getting AI transaction optimization...")
    optimization = advisor.optimize_transaction("dca", 50.0, 1.5)
    print(f"\nProceed with transaction: {optimization['proceed']}")
    print(f"Gas price adjustment: {optimization['gas_adjustment']}")
    print(f"Slippage tolerance: {optimization['slippage']}%")
    print(f"Reasoning: {optimization['reasoning']}")
    
    # Generate insight
    print("\n💡 Generating AI insight...")
    transactions = [
        {"timestamp": "2024-03-13T10:00:00", "amount": 0.00123, "price": 79500},
        {"timestamp": "2024-03-06T10:00:00", "amount": 0.00125, "price": 78200},
    ]
    price_data = {"current_price": btc_price, "price_history": price_history[-10:]}
    insight = advisor.generate_insight("DCA", transactions, price_data)
    print(f"\nAI Insight: {insight}")
    
    print("\n✅ Demo completed successfully!")

if __name__ == "__main__":
    main()