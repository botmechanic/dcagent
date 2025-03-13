import logging
import time
from datetime import datetime, timedelta
from typing import Optional
import json
import os

from dcagent.config import (
    DCA_AMOUNT, 
    DCA_INTERVAL, 
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
    web3,
    send_contract_transaction
)
from dcagent.utils.pyth_utils import get_btc_price
from dcagent.utils.logging_utils import log_event, log_transaction

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
            
            # Implement actual swap from USDC to cbBTC
            
            # 1. Convert amounts to wei considering token decimals
            usdc_decimals = 6  # USDC has 6 decimals
            usdc_amount_wei = int(DCA_AMOUNT * (10**usdc_decimals))
            
            # 2. Calculate minimum amount out with 0.5% slippage
            slippage = 0.005  # 0.5%
            min_btc_amount = btc_amount * (1 - slippage)
            cbbtc_decimals = 18  # cbBTC has 18 decimals (like most ERC20 tokens)
            min_btc_amount_wei = int(min_btc_amount * (10**cbbtc_decimals))
            
            # 3. Approve the router to spend USDC
            logger.info(f"Approving Aerodrome Router to spend {DCA_AMOUNT} USDC")
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
            
            logger.info(f"Executing swap: {DCA_AMOUNT} USDC -> ~{btc_amount:.8f} cbBTC")
            
            # Create the route for the swap
            routes = [{
                "from": USDC_CONTRACT_ADDRESS,           # tokenIn
                "to": CBBTC_CONTRACT_ADDRESS,            # tokenOut
                "stable": False,                         # volatile pair
                "factory": web3.to_checksum_address("0xAAA20D08e59F6561f242b08513D36266C5A29415")  # Aerodrome factory
            }]
            
            # Execute the swap with retry logic
            swap_function = router_contract.functions.swapExactTokensForTokens(
                usdc_amount_wei,                          # amountIn
                min_btc_amount_wei,                       # amountOutMin
                routes,                                   # routes array
                account.address,                          # to
                deadline                                  # deadline
            )
            
            logger.info(f"Executing swap with retry: {DCA_AMOUNT} USDC -> ~{btc_amount:.8f} cbBTC")
            
            # Use our retry-enabled transaction sender
            receipt = send_contract_transaction(
                contract_function=swap_function,
                account=account,
                gas_limit=300000,  # Set appropriate gas limit
                max_retries=3
            )
            
            if not receipt or receipt.status != 1:
                logger.error(f"Swap transaction failed. Receipt: {receipt}")
                return False
            
            tx_hash = receipt.transactionHash.hex()
            logger.info(f"Swap successful! Transaction hash: {tx_hash}")
            
            # Get new cbBTC balance to confirm the swap worked
            new_cbbtc_balance = get_token_balance(CBBTC_CONTRACT_ADDRESS, account.address)
            logger.info(f"New cbBTC balance: {new_cbbtc_balance}")
            
            # Log the transaction for the dashboard
            log_transaction(
                tx_type="DCA Buy",
                tx_hash=tx_hash,
                amount=btc_amount,
                token="cbBTC",
                additional_data={
                    "strategy": "dca",
                    "usdc_amount": DCA_AMOUNT,
                    "btc_price": btc_price,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Update the execution time for next run
            self.last_execution = datetime.now()
            self.setup_next_execution()
            logger.info(f"Next DCA execution scheduled for: {self.next_execution}")
            
            # Log the completion event
            log_event("dca_execution", {
                "strategy": "dca",
                "amount": DCA_AMOUNT,
                "btc_price": btc_price,
                "btc_amount": btc_amount,
                "next_execution": self.next_execution.isoformat(),
                "status": "success"
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing DCA strategy: {e}")
            return False