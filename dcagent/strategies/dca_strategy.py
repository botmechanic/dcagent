import logging
import time
from datetime import datetime, timedelta
from typing import Optional

from dcagent.config import DCA_AMOUNT, DCA_INTERVAL, CBBTC_CONTRACT_ADDRESS, USDC_CONTRACT_ADDRESS
from dcagent.strategies.base_strategy import BaseStrategy
from dcagent.utils.blockchain import get_account, get_token_balance, approve_token_spending
from dcagent.utils.pyth_utils import get_btc_price

logger = logging.getLogger(__name__)

class DCAStrategy(BaseStrategy):
    """
    Dollar-Cost Averaging strategy for buying BTC at regular intervals
    """
    
    def __init__(self):
        super().__init__("DCA")
        self.setup_next_execution()
    
    def setup_next_execution(self):
        """Set up the next execution time based on the DCA interval"""
        now = datetime.now()
        
        if DCA_INTERVAL == "daily":
            # Execute at the same time every day
            self.next_execution = now + timedelta(days=1)
        elif DCA_INTERVAL == "weekly":
            # Execute on the same day of week
            self.next_execution = now + timedelta(days=7)
        elif DCA_INTERVAL == "monthly":
            # Execute on the same day of month if possible
            current_day = now.day
            next_month = now.replace(day=1) + timedelta(days=32)
            last_day_of_next_month = (next_month.replace(day=1) - timedelta(days=1)).day
            next_day = min(current_day, last_day_of_next_month)
            self.next_execution = next_month.replace(day=next_day)
        else:
            # Default to daily if interval is invalid
            logger.warning(f"Invalid DCA interval: {DCA_INTERVAL}, defaulting to daily")
            self.next_execution = now + timedelta(days=1)
    
    def should_execute(self) -> bool:
        """Determine if the strategy should execute now"""
        now = datetime.now()
        return now >= self.next_execution
    
    def execute(self) -> bool:
        """Execute the DCA strategy by buying BTC"""
        logger.info("Executing DCA Strategy")
        
        try:
            # Get the current BTC price
            btc_price = get_btc_price()
            if not btc_price:
                logger.error("Failed to get BTC price, aborting DCA execution")
                return False
            
            logger.info(f"Current BTC price: ${btc_price:,.2f}")
            
            # Calculate the amount of BTC to buy
            btc_amount = DCA_AMOUNT / btc_price
            logger.info(f"Attempting to buy {btc_amount:.8f} BTC (${DCA_AMOUNT:.2f})")
            
            # Check if we have enough USDC
            account = get_account()
            usdc_balance = get_token_balance(USDC_CONTRACT_ADDRESS, account.address)
            
            if usdc_balance < DCA_AMOUNT:
                logger.error(f"Insufficient USDC balance. Have: ${usdc_balance:.2f}, Need: ${DCA_AMOUNT:.2f}")
                return False
            
            # TODO: Implement actual swap from USDC to cbBTC
            # This would involve:
            # 1. Approving the swap contract to spend USDC
            # 2. Executing the swap via a DEX on Base
            
            # For now, we'll just log that we would execute the swap
            logger.info(f"Would swap ${DCA_AMOUNT:.2f} USDC for {btc_amount:.8f} BTC (${btc_price:,.2f}/BTC)")
            
            # Update the execution time for next run
            self.last_execution = datetime.now()
            self.setup_next_execution()
            logger.info(f"Next DCA execution scheduled for: {self.next_execution}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing DCA strategy: {e}")
            return False