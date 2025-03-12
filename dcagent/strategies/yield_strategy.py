import logging
from datetime import datetime, timedelta
from decimal import Decimal

from dcagent.config import (
    ENABLE_YIELD_OPTIMIZATION, 
    REINVEST_YIELD, 
    CBBTC_CONTRACT_ADDRESS,
    USDC_CONTRACT_ADDRESS
)
from dcagent.strategies.base_strategy import BaseStrategy
from dcagent.utils.aerodrome import (
    claim_rewards, 
    get_earned_rewards, 
    stake_lp_tokens_in_gauge,
    add_liquidity,
    get_staked_lp_balance
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
            rewards_balance = get_earned_rewards()
            if rewards_balance > 0:
                self.next_claim = now + self.claim_interval
                return True
                
        return False
    
    def execute(self) -> bool:
        """Execute the yield optimization strategy"""
        logger.info("Executing Yield Optimization Strategy")
        
        try:
            now = datetime.now()
            account = get_account()
            
            # If it's time to claim rewards
            if now >= self.next_claim:
                rewards = get_earned_rewards()
                if rewards > 0:
                    logger.info(f"Claiming {rewards:.6f} AERO rewards from Aerodrome gauge")
                    tx_hash = claim_rewards()
                    if tx_hash:
                        logger.info(f"Successfully claimed rewards. Transaction hash: {tx_hash}")
                    else:
                        logger.warning("Failed to claim rewards")
                    
                self.next_claim = now + self.claim_interval
                
                if REINVEST_YIELD and rewards > 0 and tx_hash:
                    # In a real implementation, we would:
                    # 1. Swap AERO rewards for cbBTC and USDC (in equal value)
                    # 2. Add liquidity with those tokens
                    # 3. Stake the new LP tokens
                    logger.info("Reinvesting yield into more cbBTC-USDC LP position")
                    
                    # For demo purposes, just log the potential reinvestment
                    # since implementing the full swap logic would require additional ABI and contract addresses
                    logger.info(f"Would convert {rewards:.6f} AERO to cbBTC-USDC LP tokens and stake them")
            
            # If it's time to check for yield optimization
            if now >= self.next_check:
                logger.info("Checking for yield optimization opportunities")
                
                # Check for unstaked cbBTC and USDC balances
                cbbtc_balance = get_token_balance(CBBTC_CONTRACT_ADDRESS, account.address)
                usdc_balance = get_token_balance(USDC_CONTRACT_ADDRESS, account.address)
                
                # Convert balances to human-readable format
                cbbtc_amount = Decimal(cbbtc_balance) / (10**18)
                usdc_amount = Decimal(usdc_balance) / (10**6)
                
                # Get current BTC price to calculate equivalent value
                btc_price = get_btc_price()
                
                if cbbtc_amount > 0 and usdc_amount > 0 and btc_price:
                    logger.info(f"Found {cbbtc_amount:.8f} cbBTC and {usdc_amount:.2f} USDC available")
                    
                    # Calculate cbBTC value in USD
                    cbbtc_value_usd = cbbtc_amount * btc_price
                    
                    # Determine how much of each token to use for liquidity provision
                    # Try to match values for balanced liquidity provision
                    if cbbtc_value_usd > usdc_amount:
                        # More cbBTC value than USDC
                        # Use all USDC and equivalent cbBTC
                        usdc_to_use = usdc_amount
                        cbbtc_to_use = usdc_amount / btc_price
                    else:
                        # More or equal USDC value than cbBTC
                        # Use all cbBTC and equivalent USDC
                        cbbtc_to_use = cbbtc_amount
                        usdc_to_use = cbbtc_value_usd
                    
                    # Only proceed if we have meaningful amounts
                    min_usdc = Decimal('10.0')  # Minimum $10 worth
                    if usdc_to_use >= min_usdc:
                        logger.info(f"Adding liquidity with {cbbtc_to_use:.8f} cbBTC and {usdc_to_use:.2f} USDC")
                        
                        # Add liquidity to Aerodrome pool
                        result = add_liquidity(cbbtc_to_use, usdc_to_use)
                        
                        if result and result.get("status") == "success":
                            logger.info(f"Successfully added liquidity. Transaction hash: {result.get('transaction_hash')}")
                            
                            # Get LP token amount received (in a real implementation, this would be parsed from the event)
                            # For now using a placeholder value
                            lp_amount = int(Decimal('1.0') * (10**18))  # Placeholder value
                            
                            # Stake LP tokens in gauge
                            logger.info(f"Staking new LP tokens in gauge")
                            stake_tx = stake_lp_tokens_in_gauge(lp_amount)
                            
                            if stake_tx:
                                logger.info(f"Successfully staked LP tokens. Transaction hash: {stake_tx}")
                            else:
                                logger.warning("Failed to stake LP tokens")
                        else:
                            logger.warning("Failed to add liquidity")
                    else:
                        logger.info(f"Balances too small for liquidity provision, need at least ${min_usdc} worth")
                
                # Get current staked balance for reporting
                staked_lp = get_staked_lp_balance()
                if staked_lp > 0:
                    logger.info(f"Current staked position: {staked_lp:.6f} LP tokens")
                
                self.next_check = now + self.check_interval
            
            self.last_execution = now
            return True
            
        except Exception as e:
            logger.error(f"Error executing yield optimization strategy: {e}")
            return False