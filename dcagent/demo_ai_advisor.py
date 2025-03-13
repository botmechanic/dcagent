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
# Check for demo mode flag
DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"

if not DEMO_MODE:
    try:
        import anthropic
    except ImportError:
        print("ERROR: The 'anthropic' package is not installed.")
        print("Please install it with: pip install anthropic")
        print("Or run in demo mode: DEMO_MODE=true ./run_ai_demo.sh")
        sys.exit(1)
    
    try:
        from dcagent.utils.claude_advisor import ClaudeAdvisor
        from dcagent.utils.pyth_utils import get_btc_price
    except ImportError as e:
        print(f"ERROR: Failed to import required modules: {e}")
        print("Run in demo mode to see simulated output: DEMO_MODE=true ./run_ai_demo.sh")
        sys.exit(1)

def main():
    """Demo script to show Claude AI integration"""
    
    if DEMO_MODE:
        # Use simulated data in demo mode
        run_demo_mode()
    else:
        # Use actual Claude API in regular mode
        run_live_mode()
    
    print("\n✅ Demo completed successfully!")

def run_live_mode():
    """Run the demo with live Claude API"""
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

def run_demo_mode():
    """Run demo mode with simulated responses"""
    import random
    import time
    
    print("\n🤖 Initializing Claude AI Advisor... [DEMO MODE]")
    time.sleep(1)
    
    print("\n📊 Getting current BTC price... [DEMO MODE]")
    btc_price = 81245.25  # Simulated price
    time.sleep(0.5)
    print(f"Current BTC price: ${btc_price:,.2f}")
    
    print("\n🧠 Getting AI market analysis... [DEMO MODE]")
    time.sleep(2)  # Simulate API call
    
    # Simulated analysis
    analysis = {
        "sentiment": random.choice(["bullish", "neutral", "bearish"]),
        "buy_opportunity": random.choice([True, True, False]),
        "slippage_recommendation": round(random.uniform(0.5, 2.0), 1),
        "strategy_recommendation": "Continue with regular DCA strategy but consider increasing position size during significant dips.",
        "reasoning": "Bitcoin is showing strong support around the $80,000 level with decreasing volatility. On-chain metrics indicate accumulation by long-term holders, though short-term momentum indicators suggest some resistance ahead. The overall market structure remains bullish with healthy funding rates and strong institutional inflows."
    }
    
    print(f"\nMarket sentiment: {analysis['sentiment']}")
    print(f"Good buying opportunity: {analysis['buy_opportunity']}")
    print(f"Slippage recommendation: {analysis['slippage_recommendation']}%")
    print(f"Strategy recommendation: {analysis['strategy_recommendation']}")
    print(f"Reasoning: {analysis['reasoning']}")
    
    print("\n⚙️ Getting AI transaction optimization... [DEMO MODE]")
    time.sleep(1.5)  # Simulate API call
    
    # Simulated optimization
    optimization = {
        "proceed": True,
        "gas_adjustment": round(random.uniform(0.9, 1.1), 2),
        "slippage": round(random.uniform(0.5, 1.5), 1),
        "reasoning": "Current gas prices on Base are stable and within acceptable ranges. Transaction should proceed with standard gas settings. The recommended slippage tolerance accounts for current market volatility while ensuring timely execution."
    }
    
    print(f"\nProceed with transaction: {optimization['proceed']}")
    print(f"Gas price adjustment: {optimization['gas_adjustment']}")
    print(f"Slippage tolerance: {optimization['slippage']}%")
    print(f"Reasoning: {optimization['reasoning']}")
    
    print("\n💡 Generating AI insight... [DEMO MODE]")
    time.sleep(2)  # Simulate API call
    
    # Simulated insight
    insight = "Your DCA strategy has been effective, averaging in at a price below current market value. Recent transactions show good timing with purchases executed during minor dips. With current market indicators suggesting continued strength, maintaining your regular DCA cadence while being prepared to increase allocation during high-volatility days would be optimal."
    
    print(f"\nAI Insight: {insight}")

if __name__ == "__main__":
    main()