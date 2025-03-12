# dcagent/strategies/yield_strategy.py
import logging
from datetime import datetime, timedelta

from dcagent.config import ENABLE_YIELD_OPTIMIZATION, REINVEST_YIELD
from dcagent.strategies.base_strategy import BaseStrategy
from dcagent.utils.aerodrome import (
    claim_rewards, get_rewards_balance, stake_lp_tokens_in_gauge
)
from dcagent.utils.blockchain import get_token_balance, get_account
from dcagent.utils.pyth_utils import get_btc_price

logger = logging.getLogger(__name__)

class YieldOptimizationStrategy(BaseStrategy):
    """
    Strategy for optimizing yield on cbBTC holdings via Aerodrome
    """
    
    def __init__(self):
        super().__init__("YieldOptimization")
        self.check_interval = timedelta(days=1)  # Check for yield optimization daily
        self.next_check = datetime.now()
        self.claim_interval = timedelta(days=7)  # Claim rewards weekly
        self.next_claim = datetime.now()
    
    def should_execute(self) -> bool:
        """Determine if the strategy should execute now"""
        if not ENABLE_YIELD_OPTIMIZATION:
            return False
            
        now = datetime.now()
        
        # Time to check for yield optimization?
        if now >= self.next_check:
            self.next_check = now + self.check_interval
            return True
            
        # Time to claim rewards?
        if now >= self.next_claim:
            rewards_balance = get_rewards_balance()
            if rewards_balance > 0:
                self.next_claim = now + self.claim_interval
                return True
                
        return False
    
    def execute(self) -> bool:
        """Execute the yield optimization strategy"""
        logger.info("Executing Yield Optimization Strategy")
        
        try:
            now = datetime.now()
            
            # If it's time to claim rewards
            if now >= self.next_claim:
                logger.info("Claiming rewards from Aerodrome gauge")
                claim_rewards()
                self.next_claim = now + self.claim_interval
                
                if REINVEST_YIELD:
                    # Logic to reinvest rewards into more cbBTC
                    logger.info("Reinvesting yield into more cbBTC")
                    # Convert rewards to cbBTC
                    # Add more to staking position
            
            # If it's time to check for yield optimization
            if now >= self.next_check:
                logger.info("Checking for yield optimization opportunities")
                # Check for unstaked cbBTC
                account = get_account()
                cbbtc_balance = get_token_balance(CBBTC_CONTRACT_ADDRESS, account.address)
                
                if cbbtc_balance > 0:
                    # Stake available cbBTC
                    logger.info(f"Staking {cbbtc_balance} cbBTC for yield")
                    # Logic to stake in Aerodrome pool/gauge
                
                self.next_check = now + self.check_interval
            
            self.last_execution = now
            return True
            
        except Exception as e:
            logger.error(f"Error executing yield optimization strategy: {e}")
            return False