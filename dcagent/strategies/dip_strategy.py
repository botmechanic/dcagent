# dcagent/strategies/dip_strategy.py
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from dcagent.config import DCA_AMOUNT, DIP_THRESHOLD, ENABLE_DIP_BUYING
from dcagent.strategies.base_strategy import BaseStrategy
from dcagent.utils.blockchain import get_account, get_token_balance
from dcagent.utils.pyth_utils import get_btc_price

logger = logging.getLogger(__name__)

class DipBuyingStrategy(BaseStrategy):
    """
    Strategy for buying BTC during price dips
    """
    
    def __init__(self):
        super().__init__("DipBuying")
        self.price_history: List[float] = []
        self.check_interval = timedelta(hours=1)  # Check for dips hourly
        self.next_check = datetime.now()
        self.last_buy = None
        self.minimum_buy_interval = timedelta(days=1)  # Don't buy dips more than once per day
    
    def update_price_history(self) -> None:
        """Update the price history with the current BTC price"""
        current_price = get_btc_price()
        if current_price:
            self.price_history.append(current_price)
            # Keep only the last 24 price points (24 hours of data at hourly intervals)
            self.price_history = self.price_history[-24:]
    
    def detect_dip(self) -> bool:
        """Detect if there's a significant price dip"""
        if len(self.price_history) < 6:  # Need at least 6 hours of data
            return False
        
        # Get current price
        current_price = self.price_history[-1]
        
        # Calculate moving average (last 6 hours excluding current price)
        moving_avg = sum(self.price_history[-7:-1]) / 6
        
        # Calculate percentage drop from moving average
        percentage_drop = (moving_avg - current_price) / moving_avg * 100
        
        # Check if drop exceeds threshold
        is_dip = percentage_drop >= DIP_THRESHOLD
        
        if is_dip:
            logger.info(f"BTC price dip detected! {percentage_drop:.2f}% below 6-hour average")
        
        return is_dip
    
    def should_execute(self) -> bool:
        """Determine if the strategy should execute now"""
        if not ENABLE_DIP_BUYING:
            return False
            
        now = datetime.now()
        
        # Time to check for a dip?
        if now >= self.next_check:
            self.update_price_history()
            self.next_check = now + self.check_interval
            
            # If we recently bought a dip, don't buy again yet
            if self.last_buy and (now - self.last_buy) < self.minimum_buy_interval:
                return False
                
            # Detect if there's a dip
            return self.detect_dip()
            
        return False
    
    def execute(self) -> bool:
        """Execute the dip buying strategy"""
        logger.info("Executing Dip Buying Strategy")
        
        try:
            # Get the current BTC price
            btc_price = get_btc_price()
            if not btc_price:
                logger.error("Failed to get BTC price, aborting dip buy execution")
                return False
                
            logger.info(f"Current BTC price: ${btc_price:,.2f}")
            
            # Calculate the amount of BTC to buy (same as regular DCA amount)
            btc_amount = DCA_AMOUNT / btc_price
            logger.info(f"Attempting to buy {btc_amount:.8f} BTC (${DCA_AMOUNT:.2f}) during dip")
            
            # Check if we have enough USDC
            account = get_account()
            usdc_balance = get_token_balance(USDC_CONTRACT_ADDRESS, account.address)
            
            if usdc_balance < DCA_AMOUNT:
                logger.error(f"Insufficient USDC balance. Have: ${usdc_balance:.2f}, Need: ${DCA_AMOUNT:.2f}")
                return False
            
            # TODO: Implement actual swap from USDC to cbBTC
            # This would be the same implementation as in the DCA strategy
            
            # For now, we'll just log that we would execute the swap
            logger.info(f"Would swap ${DCA_AMOUNT:.2f} USDC for {btc_amount:.8f} BTC during dip (${btc_price:,.2f}/BTC)")
            
            # Record this buy
            self.last_buy = datetime.now()
            self.last_execution = self.last_buy
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing dip buying strategy: {e}")
            return False