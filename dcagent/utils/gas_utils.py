import logging
import time
from typing import Dict, Any
from dcagent.utils.claude_advisor import ClaudeAdvisor
from dcagent.utils.blockchain import web3

logger = logging.getLogger(__name__)

class GasOptimizer:
    """
    AI-powered gas price optimization for transactions
    """
    
    def __init__(self):
        self.claude_advisor = ClaudeAdvisor()
    
    def get_optimized_gas_price(self, strategy: str, amount: float) -> int:
        """
        Get AI-optimized gas price for a transaction
        
        Args:
            strategy: Strategy name (dca, dip, etc.)
            amount: Transaction amount in USD
            
        Returns:
            Optimized gas price in wei
        """
        try:
            # Get current gas price
            current_gas_price = web3.eth.gas_price
            current_gas_gwei = web3.from_wei(current_gas_price, 'gwei')
            
            # Get optimization recommendations from Claude
            optimization = self.claude_advisor.optimize_transaction(
                strategy, 
                amount, 
                current_gas_gwei
            )
            
            if not optimization['proceed']:
                logger.info(f"AI recommends waiting for better gas prices: {optimization['reasoning']}")
                # Sleep for 5 minutes and try again
                time.sleep(300)
                return self.get_optimized_gas_price(strategy, amount)
            
            # Apply the recommended gas adjustment
            optimized_gas_price = int(current_gas_price * optimization['gas_adjustment'])
            
            logger.info(f"AI optimized gas price: {web3.from_wei(optimized_gas_price, 'gwei')} gwei (adjustment factor: {optimization['gas_adjustment']})")
            return optimized_gas_price
        
        except Exception as e:
            logger.error(f"Error optimizing gas price: {e}, using default gas price")
            return web3.eth.gas_price