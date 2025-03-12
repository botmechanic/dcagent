import logging
import time
import json
import os
from datetime import datetime, timedelta
from typing import List, Optional

from dcagent.config import (
    DCA_AMOUNT, 
    DIP_THRESHOLD, 
    ENABLE_DIP_BUYING, 
    CBBTC_CONTRACT_ADDRESS, 
    USDC_CONTRACT_ADDRESS,
    AERODROME_ROUTER
)
from dcagent.strategies.base_strategy import BaseStrategy
from dcagent.utils.blockchain import (
    get_account, 
    get_token_balance, 
    approve_token_spending,
    get_contract,
    web3
)
from dcagent.utils.pyth_utils import get_btc_price

logger = logging.getLogger(__name__)

# Get directory of this file to construct paths correctly
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load Router ABI
def load_abi(filename):
    """Load ABI from a JSON file"""
    abi_path = os.path.join(BASE_DIR, 'abis', filename)
    with open(abi_path, 'r') as f:
        return json.load(f)

ROUTER_ABI = load_abi('router.json')

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
            
            # Implement actual swap from USDC to cbBTC
            
            # 1. Convert amounts to wei considering token decimals
            usdc_decimals = 6  # USDC has 6 decimals
            usdc_amount_wei = int(DCA_AMOUNT * (10**usdc_decimals))
            
            # 2. Calculate minimum amount out with 0.5% slippage
            # For dip buying, we can use a slightly higher slippage to ensure execution
            slippage = 0.01  # 1% slippage for dip buying to ensure execution
            min_btc_amount = btc_amount * (1 - slippage)
            cbbtc_decimals = 18  # cbBTC has 18 decimals (like most ERC20 tokens)
            min_btc_amount_wei = int(min_btc_amount * (10**cbbtc_decimals))
            
            # 3. Approve the router to spend USDC
            logger.info(f"Approving Aerodrome Router to spend {DCA_AMOUNT} USDC for dip buying")
            approve_receipt = approve_token_spending(
                USDC_CONTRACT_ADDRESS, 
                AERODROME_ROUTER,
                DCA_AMOUNT
            )
            
            if not approve_receipt or approve_receipt.status != 1:
                logger.error("Failed to approve USDC spending")
                return False
            
            logger.info(f"USDC spending approved. Transaction hash: {approve_receipt.transactionHash.hex()}")
            
            # 4. Execute the swap through Aerodrome Router
            router_contract = get_contract(AERODROME_ROUTER, ROUTER_ABI)
            
            # Create swap transaction
            # Set deadline to 10 minutes from now
            deadline = int(time.time() + 600)
            
            logger.info(f"Executing dip buy swap: {DCA_AMOUNT} USDC -> ~{btc_amount:.8f} cbBTC at ${btc_price:,.2f}")
            
            # Create the route for the swap
            routes = [{
                "from": USDC_CONTRACT_ADDRESS,           # tokenIn
                "to": CBBTC_CONTRACT_ADDRESS,            # tokenOut
                "stable": False,                         # volatile pair
                "factory": web3.to_checksum_address("0xAAA20D08e59F6561f242b08513D36266C5A29415")  # Aerodrome factory
            }]
            
            swap_tx = router_contract.functions.swapExactTokensForTokens(
                usdc_amount_wei,                          # amountIn
                min_btc_amount_wei,                       # amountOutMin
                routes,                                   # routes array
                account.address,                          # to
                deadline                                  # deadline
            ).build_transaction({
                'from': account.address,
                'nonce': web3.eth.get_transaction_count(account.address),
                'gas': 300000,  # Set appropriate gas limit
                'gasPrice': web3.eth.gas_price,
            })
            
            # Sign and send transaction
            signed_tx = account.sign_transaction(swap_tx)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for transaction receipt
            logger.info(f"Dip buy swap transaction sent. Waiting for confirmation...")
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status != 1:
                logger.error(f"Dip buy swap transaction failed. Transaction hash: {tx_hash.hex()}")
                return False
            
            logger.info(f"Dip buy swap successful! Transaction hash: {tx_hash.hex()}")
            
            # Get new cbBTC balance to confirm the swap worked
            new_cbbtc_balance = get_token_balance(CBBTC_CONTRACT_ADDRESS, account.address)
            logger.info(f"New cbBTC balance after dip buy: {new_cbbtc_balance}")
            
            # Record this buy
            self.last_buy = datetime.now()
            self.last_execution = self.last_buy
            logger.info(f"Dip buying recorded. Next dip buy will be available after: {self.last_buy + self.minimum_buy_interval}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing dip buying strategy: {e}")
            return False