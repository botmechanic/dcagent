import json
import logging
import os
from typing import Optional, Tuple, Dict, Any
from decimal import Decimal

from web3 import Web3

from dcagent.config import CBBTC_CONTRACT_ADDRESS, USDC_CONTRACT_ADDRESS
from dcagent.utils.blockchain import web3, get_contract, get_account, approve_token_spending

logger = logging.getLogger(__name__)

# Aerodrome contract addresses
AERODROME_ROUTER = "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"
CBBTC_USDC_POOL = "0x4e962BB3889Bf030368F56810A9c96B83CB3E778"
CBBTC_USDC_GAUGE = "0x6399ed6725cC163D019aA64FF55b22149D7179A8"

# Get directory of this file to construct paths correctly
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load ABIs from files
def load_abi(filename):
    """Load ABI from a JSON file"""
    abi_path = os.path.join(BASE_DIR, 'abis', filename)
    with open(abi_path, 'r') as f:
        return json.load(f)

# Load ABIs
POOL_ABI = load_abi('pool.json')
GAUGE_ABI = load_abi('gauge.json')
ROUTER_ABI = load_abi('router.json')

def get_pool_tokens() -> Tuple[str, str]:
    """Get the token addresses for the pool"""
    pool_contract = get_contract(CBBTC_USDC_POOL, POOL_ABI)
    token0 = pool_contract.functions.token0().call()
    token1 = pool_contract.functions.token1().call()
    return token0, token1

def get_pool_info() -> Dict[str, Any]:
    """Get detailed information about the cbBTC-USDC pool"""
    try:
        pool_contract = get_contract(CBBTC_USDC_POOL, POOL_ABI)
        token0, token1 = get_pool_tokens()
        
        # Get current price and liquidity
        slot0 = pool_contract.functions.slot0().call()
        liquidity = pool_contract.functions.liquidity().call()
        
        # Check if tokens are in expected order
        cbbtc_is_token0 = token0.lower() == CBBTC_CONTRACT_ADDRESS.lower()
        
        return {
            "token0": token0,
            "token1": token1,
            "cbbtc_is_token0": cbbtc_is_token0,
            "sqrtPriceX96": slot0[0],
            "tick": slot0[1],
            "liquidity": liquidity,
            "fee": pool_contract.functions.fee().call()
        }
    except Exception as e:
        logger.error(f"Error getting pool info: {e}")
        return {}

def add_liquidity(cbbtc_amount: Decimal, usdc_amount: Decimal, slippage: float = 0.01) -> Optional[Dict[str, Any]]:
    """
    Add liquidity to the cbBTC-USDC pool
    
    Args:
        cbbtc_amount: Amount of cbBTC to provide
        usdc_amount: Amount of USDC to provide
        slippage: Maximum allowed slippage (default 1%)
        
    Returns:
        Dict containing transaction info or None if failed
    """
    try:
        # Get account
        account = get_account()
        
        # Get token info
        token0, token1 = get_pool_tokens()
        pool_info = get_pool_info()
        
        # Need to know which token is which for proper ordering
        cbbtc_is_token0 = pool_info["cbbtc_is_token0"]
        
        # Convert decimal amounts to Wei
        cbbtc_decimals = 8  # cbBTC typically has 8 decimals
        usdc_decimals = 6   # USDC typically has 6 decimals
        
        cbbtc_amount_wei = int(cbbtc_amount * (10 ** cbbtc_decimals))
        usdc_amount_wei = int(usdc_amount * (10 ** usdc_decimals))
        
        # Calculate minimum amounts based on slippage
        cbbtc_min = int(cbbtc_amount_wei * (1 - slippage))
        usdc_min = int(usdc_amount_wei * (1 - slippage))
        
        # Set up parameters for addLiquidity
        token_a = token0 if cbbtc_is_token0 else token1
        token_b = token1 if cbbtc_is_token0 else token0
        
        amount_a_desired = cbbtc_amount_wei if cbbtc_is_token0 else usdc_amount_wei
        amount_b_desired = usdc_amount_wei if cbbtc_is_token0 else cbbtc_amount_wei
        
        amount_a_min = cbbtc_min if cbbtc_is_token0 else usdc_min
        amount_b_min = usdc_min if cbbtc_is_token0 else cbbtc_min
        
        # Approve tokens for router
        approve_token_spending(CBBTC_CONTRACT_ADDRESS, AERODROME_ROUTER, cbbtc_amount_wei)
        approve_token_spending(USDC_CONTRACT_ADDRESS, AERODROME_ROUTER, usdc_amount_wei)
        
        # Get router contract
        router_contract = get_contract(AERODROME_ROUTER, ROUTER_ABI)
        
        # Current timestamp + 20 minutes (deadline)
        deadline = web3.eth.get_block('latest').timestamp + 1200
        
        # Call addLiquidity
        tx = router_contract.functions.addLiquidity(
            token_a,
            token_b,
            False,  # not stable
            amount_a_desired,
            amount_b_desired,
            amount_a_min,
            amount_b_min,
            account.address,
            deadline
        ).build_transaction({
            'from': account.address,
            'nonce': web3.eth.get_transaction_count(account.address),
            'gas': 500000,  # Adjust gas as needed
            'gasPrice': web3.eth.gas_price
        })
        
        # Sign and send transaction
        signed_tx = account.sign_transaction(tx)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for transaction receipt
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        
        return {
            "status": "success" if receipt.status == 1 else "failed",
            "tx_hash": tx_hash.hex(),
            "cbbtc_amount": cbbtc_amount,
            "usdc_amount": usdc_amount
        }
    
    except Exception as e:
        logger.error(f"Error adding liquidity: {e}")
        return None

def stake_lp_tokens_in_gauge(lp_amount: int) -> Optional[str]:
    """
    Stake LP tokens in the Gauge to earn rewards
    
    Args:
        lp_amount: Amount of LP tokens to stake (in Wei)
        
    Returns:
        Transaction hash or None if failed
    """
    try:
        account = get_account()
        
        # First approve the gauge to spend the LP tokens
        pool_contract = get_contract(CBBTC_USDC_POOL, POOL_ABI)
        approve_token_spending(CBBTC_USDC_POOL, CBBTC_USDC_GAUGE, lp_amount)
        
        # Get gauge contract
        gauge_contract = get_contract(CBBTC_USDC_GAUGE, GAUGE_ABI)
        
        # Build deposit transaction
        tx = gauge_contract.functions.deposit(lp_amount).build_transaction({
            'from': account.address,
            'nonce': web3.eth.get_transaction_count(account.address),
            'gas': 300000,  # Adjust as needed
            'gasPrice': web3.eth.gas_price
        })
        
        # Sign and send transaction
        signed_tx = account.sign_transaction(tx)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for transaction receipt
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            return tx_hash.hex()
        else:
            logger.error("Staking transaction failed")
            return None
            
    except Exception as e:
        logger.error(f"Error staking LP tokens: {e}")
        return None

def claim_rewards() -> Optional[str]:
    """
    Claim rewards from the Gauge
    
    Returns:
        Transaction hash or None if failed
    """
    try:
        account = get_account()
        
        # Get gauge contract
        gauge_contract = get_contract(CBBTC_USDC_GAUGE, GAUGE_ABI)
        
        # Build getReward transaction
        tx = gauge_contract.functions.getReward().build_transaction({
            'from': account.address,
            'nonce': web3.eth.get_transaction_count(account.address),
            'gas': 300000,  # Adjust as needed
            'gasPrice': web3.eth.gas_price
        })
        
        # Sign and send transaction
        signed_tx = account.sign_transaction(tx)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for transaction receipt
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            return tx_hash.hex()
        else:
            logger.error("Claim rewards transaction failed")
            return None
            
    except Exception as e:
        logger.error(f"Error claiming rewards: {e}")
        return None

def get_staked_lp_balance() -> Decimal:
    """
    Get the amount of LP tokens staked in the Gauge
    
    Returns:
        Balance of staked LP tokens
    """
    try:
        account = get_account()
        
        # Get gauge contract
        gauge_contract = get_contract(CBBTC_USDC_GAUGE, GAUGE_ABI)
        
        # Get balance
        balance = gauge_contract.functions.balanceOf(account.address).call()
        
        # LP tokens usually have 18 decimals
        return Decimal(balance) / Decimal(10**18)
        
    except Exception as e:
        logger.error(f"Error getting staked LP balance: {e}")
        return Decimal(0)

def get_earned_rewards() -> Decimal:
    """
    Get the amount of rewards earned but not yet claimed
    
    Returns:
        Amount of earned rewards
    """
    try:
        account = get_account()
        
        # Get gauge contract
        gauge_contract = get_contract(CBBTC_USDC_GAUGE, GAUGE_ABI)
        
        # Get earned rewards
        earned = gauge_contract.functions.earned(account.address).call()
        
        # Rewards token usually has 18 decimals (assuming AERO token)
        return Decimal(earned) / Decimal(10**18)
        
    except Exception as e:
        logger.error(f"Error getting earned rewards: {e}")
        return Decimal(0)

def withdraw_lp_tokens_from_gauge(lp_amount: int) -> Optional[str]:
    """
    Withdraw LP tokens from the Gauge
    
    Args:
        lp_amount: Amount of LP tokens to withdraw (in Wei)
        
    Returns:
        Transaction hash or None if failed
    """
    try:
        account = get_account()
        
        # Get gauge contract
        gauge_contract = get_contract(CBBTC_USDC_GAUGE, GAUGE_ABI)
        
        # Build withdraw transaction
        tx = gauge_contract.functions.withdraw(lp_amount).build_transaction({
            'from': account.address,
            'nonce': web3.eth.get_transaction_count(account.address),
            'gas': 300000,  # Adjust as needed
            'gasPrice': web3.eth.gas_price
        })
        
        # Sign and send transaction
        signed_tx = account.sign_transaction(tx)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for transaction receipt
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            return tx_hash.hex()
        else:
            logger.error("Withdraw transaction failed")
            return None
            
    except Exception as e:
        logger.error(f"Error withdrawing LP tokens: {e}")
        return None

def get_pool_token_balances() -> Dict[str, Decimal]:
    """
    Get the balances of cbBTC and USDC in the wallet
    
    Returns:
        Dict with token balances
    """
    try:
        account = get_account()
        
        # Get token balances
        cbbtc_balance_wei = get_token_balance(CBBTC_CONTRACT_ADDRESS, account.address)
        usdc_balance_wei = get_token_balance(USDC_CONTRACT_ADDRESS, account.address)
        
        # Convert to human-readable values
        cbbtc_balance = Decimal(cbbtc_balance_wei) / Decimal(10**8)  # 8 decimals
        usdc_balance = Decimal(usdc_balance_wei) / Decimal(10**6)    # 6 decimals
        
        return {
            "cbbtc": cbbtc_balance,
            "usdc": usdc_balance
        }
        
    except Exception as e:
        logger.error(f"Error getting token balances: {e}")
        return {"cbbtc": Decimal(0), "usdc": Decimal(0)}

def get_pool_lp_token_balance() -> Decimal:
    """
    Get the balance of LP tokens (not staked) in the wallet
    
    Returns:
        Balance of LP tokens
    """
    try:
        account = get_account()
        
        # Get token balance
        lp_balance_wei = get_token_balance(CBBTC_USDC_POOL, account.address)
        
        # LP tokens typically have 18 decimals
        return Decimal(lp_balance_wei) / Decimal(10**18)
        
    except Exception as e:
        logger.error(f"Error getting LP token balance: {e}")
        return Decimal(0)

def get_gauge_apr() -> Decimal:
    """
    Estimate the APR for staking LP tokens in the gauge
    
    Returns:
        Estimated APR as a percentage
    """
    try:
        # This is a simplified APR calculation and may not be accurate
        # Actual implementation would depend on Aerodrome's specific mechanics
        
        # Get gauge contract
        gauge_contract = get_contract(CBBTC_USDC_GAUGE, GAUGE_ABI)
        
        # Get reward rate (tokens per second)
        reward_rate = Decimal(gauge_contract.functions.rewardRate().call()) / Decimal(10**18)
        
        # Get total staked LP tokens
        total_supply = Decimal(gauge_contract.functions.totalSupply().call()) / Decimal(10**18)
        
        if total_supply == 0:
            return Decimal(0)
        
        # Get AERO token price (simplified - would need price feed)
        aero_price = Decimal(1)  # Placeholder, need actual price
        
        # Calculate daily rewards
        daily_rewards = reward_rate * 86400  # seconds in a day
        
        # Calculate value of staked LP tokens
        pool_info = get_pool_info()
        lp_token_price = Decimal(1)  # Placeholder, need actual price
        total_staked_value = total_supply * lp_token_price
        
        if total_staked_value == 0:
            return Decimal(0)
        
        # Calculate daily APR
        daily_apr = (daily_rewards * aero_price) / total_staked_value
        
        # Convert to annual APR
        annual_apr = daily_apr * 365 * 100  # As percentage
        
        return annual_apr
        
    except Exception as e:
        logger.error(f"Error calculating gauge APR: {e}")
        return Decimal(0)

def reinvest_rewards(min_usdc_amount: Decimal = Decimal('1.0')) -> Optional[Dict[str, Any]]:
    """
    Claim and reinvest rewards by buying more cbBTC and adding to LP
    
    Args:
        min_usdc_amount: Minimum amount of USDC to reinvest (to avoid dust)
        
    Returns:
        Transaction info or None if failed
    """
    try:
        # Claim rewards
        claim_tx = claim_rewards()
        if not claim_tx:
            logger.error("Failed to claim rewards")
            return None
            
        # TODO: Implement logic to:
        # 1. Swap claimed rewards (AERO) to USDC
        # 2. Use USDC to buy cbBTC (for balanced LP position)
        # 3. Add liquidity with new USDC and cbBTC
        # 4. Stake new LP tokens
        
        # This requires additional logic for swapping tokens
        logger.info("Reinvestment process would execute here")
        
        return {
            "status": "success",
            "claim_tx": claim_tx,
            # Additional transaction details would be added here
        }
            
    except Exception as e:
        logger.error(f"Error reinvesting rewards: {e}")
        return None