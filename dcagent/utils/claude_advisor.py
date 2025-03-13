import os
import logging
import json
import anthropic
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class ClaudeAdvisor:
    """
    Use Claude AI to enhance decision making for the DCAgent
    """
    
    def __init__(self):
        """Initialize the Claude AI advisor"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("ANTHROPIC_API_KEY not found in environment variables")
            print("\n" + "="*80)
            print("ERROR: ANTHROPIC_API_KEY environment variable is not set.")
            print("Please set it before running this script:")
            print("export ANTHROPIC_API_KEY=your_api_key_here")
            print("="*80 + "\n")
            raise ValueError("ANTHROPIC_API_KEY is required")
            
        self.client = anthropic.Anthropic(api_key=api_key)
        logger.info("Claude AI Advisor initialized successfully")
    
    def market_analysis(self, btc_price: float, price_history: List[float]) -> Dict[str, Any]:
        """
        Get market analysis and recommendations from Claude
        
        Args:
            btc_price: Current BTC price
            price_history: Recent BTC price history
            
        Returns:
            Dictionary with market analysis and recommendations
        """
        try:
            # Format price history for context
            price_context = "\n".join([f"- ${price:.2f}" for price in price_history[-10:]])
            
            # Create prompt for Claude
            prompt = f"""
            You are a cryptocurrency market analyst assisting an autonomous DCA (Dollar-Cost Averaging) agent for Bitcoin.
            The agent automatically buys small amounts of Bitcoin on Base L2 using cbBTC tokens.
            
            Current BTC price: ${btc_price:.2f}
            
            Recent BTC price history (last 10 data points):
            {price_context}
            
            Please provide a brief market analysis and actionable recommendations:
            1. Market sentiment (bullish, bearish, or neutral)
            2. Whether current price represents a good buying opportunity
            3. A suggestion for slippage tolerance (0.5-2%)
            4. Whether to stick with regular DCA or adjust strategy
            
            Format your response as a JSON object with the following fields:
            - sentiment: "bullish", "bearish", or "neutral"
            - buy_opportunity: true or false
            - slippage_recommendation: float (0.5-2.0)
            - strategy_recommendation: string
            - reasoning: string (brief explanation)
            
            ONLY return a valid JSON object, nothing else.
            """
            
            # Get response from Claude
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                temperature=0.2,
                system="You are a cryptocurrency market analysis assistant providing precise, concise JSON responses.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse JSON response
            response_text = response.content[0].text
            analysis = json.loads(response_text)
            
            logger.info(f"Received market analysis from Claude: {analysis['sentiment']} sentiment, buy opportunity: {analysis['buy_opportunity']}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error getting market analysis from Claude: {e}")
            # Return default analysis in case of error
            return {
                "sentiment": "neutral",
                "buy_opportunity": True,
                "slippage_recommendation": 0.5,
                "strategy_recommendation": "Continue with regular DCA strategy",
                "reasoning": "Error contacting AI advisor, defaulting to conservative strategy"
            }
    
    def optimize_transaction(self, strategy: str, amount: float, gas_price: int) -> Dict[str, Any]:
        """
        Get transaction optimization recommendations from Claude
        
        Args:
            strategy: Current strategy being executed (e.g., "dca", "dip")
            amount: Amount to be transacted in USD
            gas_price: Current gas price in gwei
            
        Returns:
            Dictionary with transaction optimization recommendations
        """
        try:
            prompt = f"""
            You are a blockchain transaction optimization assistant for an autonomous Bitcoin DCA agent.
            
            Current transaction details:
            - Strategy: {strategy}
            - Transaction amount: ${amount:.2f}
            - Current Base L2 gas price: {gas_price} gwei
            
            Please provide recommendations to optimize this transaction:
            1. Should the transaction proceed now or wait for lower gas?
            2. Recommended gas price adjustment (lower, maintain, or increase)
            3. Recommended slippage tolerance
            
            Format your response as a JSON object with the following fields:
            - proceed: true or false
            - gas_adjustment: float (0.8-1.5 multiplier)
            - slippage: float (0.5-2.0)
            - reasoning: string (brief explanation)
            
            ONLY return a valid JSON object, nothing else.
            """
            
            # Get response from Claude
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0.1,
                system="You are a blockchain transaction optimization assistant providing precise, concise JSON responses.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse JSON response
            response_text = response.content[0].text
            recommendations = json.loads(response_text)
            
            logger.info(f"Received transaction optimization from Claude: proceed: {recommendations['proceed']}, gas adjustment: {recommendations['gas_adjustment']}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting transaction optimization from Claude: {e}")
            # Return default recommendations in case of error
            return {
                "proceed": True,
                "gas_adjustment": 1.0,
                "slippage": 0.5,
                "reasoning": "Error contacting AI advisor, using default transaction parameters"
            }
    
    def generate_insight(self, strategy_name: str, transaction_history: List[Dict], price_data: Dict) -> str:
        """
        Generate a human-readable insight about recent transactions and strategy performance
        
        Args:
            strategy_name: Name of the strategy
            transaction_history: Recent transaction history
            price_data: Recent price data
            
        Returns:
            Human-readable insight string
        """
        try:
            # Format transaction history for context
            tx_context = json.dumps(transaction_history[-5:] if transaction_history else [])
            price_context = json.dumps(price_data)
            
            prompt = f"""
            You are an AI assistant for a Bitcoin DCA (Dollar-Cost Averaging) agent.
            The agent automatically buys small amounts of Bitcoin on Base L2 using cbBTC tokens.
            
            Generate a brief, human-readable insight about the recent performance of the "{strategy_name}" strategy.
            
            Recent transactions:
            {tx_context}
            
            Price data:
            {price_context}
            
            The insight should be concise (3-5 sentences) and include:
            1. Performance assessment
            2. Any pattern observations
            3. A forward-looking recommendation
            
            Respond with ONLY the insight text, no introductions, no JSON formatting.
            """
            
            # Get response from Claude
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                temperature=0.7,  # Higher temperature for more natural language
                system="You are a cryptocurrency strategy assistant providing concise, natural language insights.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Get insight text
            insight = response.content[0].text.strip()
            logger.info(f"Generated insight from Claude: {insight[:50]}...")
            return insight
            
        except Exception as e:
            logger.error(f"Error generating insight from Claude: {e}")
            return "Unable to generate AI insight at this time. Continuing with standard strategy execution."