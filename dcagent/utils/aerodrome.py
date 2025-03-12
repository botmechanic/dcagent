import json
import logging
import os
import time
from typing import Optional, Tuple, Dict, Any
from decimal import Decimal

from web3 import Web3

from dcagent.config import CBBTC_CONTRACT_ADDRESS, USDC_CONTRACT_ADDRESS, AERODROME_ROUTER as ROUTER_ADDRESS
from dcagent.config import CBBTC_POOL as POOL_ADDRESS, CBBTC_GAUGE as GAUGE_ADDRESS
from dcagent.utils.agent_kit import get_token_balance
from dcagent.utils.blockchain import web3, get_account, get_contract, approve_token_spending

logger = logging.getLogger(__name__)

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

# Token decimals
CBBTC_DECIMALS = 18  # Standard ERC20 decimals
USDC_DECIMALS = 6    # USDC has 6 decimals
LP_TOKEN_DECIMALS = 18  # LP token decimals

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
        account = get_account()
        router_contract = get_contract(ROUTER_ADDRESS, ROUTER_ABI)
        
        # Convert amounts to wei
        cbbtc_amount_wei = int(cbbtc_amount * (10**CBBTC_DECIMALS))
        usdc_amount_wei = int(usdc_amount * (10**USDC_DECIMALS))
        
        # Calculate minimum amounts with slippage tolerance
        cbbtc_min_amount = int(cbbtc_amount_wei * (1 - slippage))
        usdc_min_amount = int(usdc_amount_wei * (1 - slippage))
        
        # Check balances
        cbbtc_balance = get_token_balance(CBBTC_CONTRACT_ADDRESS, account.address)
        usdc_balance = get_token_balance(USDC_CONTRACT_ADDRESS, account.address)
        
        if cbbtc_balance < cbbtc_amount_wei:
            logger.error(f"Insufficient cbBTC balance. Have: {cbbtc_balance / (10**CBBTC_DECIMALS)}, Need: {cbbtc_amount}")
            return None
            
        if usdc_balance < usdc_amount_wei:
            logger.error(f"Insufficient USDC balance. Have: {usdc_balance / (10**USDC_DECIMALS)}, Need: {usdc_amount}")
            return None
        
        # Approve Router to spend tokens
        logger.info(f"Approving Router to spend {cbbtc_amount} cbBTC")
        cbbtc_approve_receipt = approve_token_spending(
            CBBTC_CONTRACT_ADDRESS,
            ROUTER_ADDRESS,
            cbbtc_amount
        )
        
        if not cbbtc_approve_receipt or cbbtc_approve_receipt.status != 1:
            logger.error("Failed to approve cbBTC spending")
            return None
            
        logger.info(f"Approving Router to spend {usdc_amount} USDC")
        usdc_approve_receipt = approve_token_spending(
            USDC_CONTRACT_ADDRESS,
            ROUTER_ADDRESS,
            usdc_amount
        )
        
        if not usdc_approve_receipt or usdc_approve_receipt.status != 1:
            logger.error("Failed to approve USDC spending")
            return None
        
        # Call router.addLiquidity
        # Set deadline to 10 minutes from now
        deadline = int(time.time() + 600)
        
        logger.info(f"Adding liquidity: {cbbtc_amount} cbBTC and {usdc_amount} USDC")
        
        tx = router_contract.functions.addLiquidity(
            CBBTC_CONTRACT_ADDRESS,                # tokenA
            USDC_CONTRACT_ADDRESS,                 # tokenB
            False,                                 # stable - assuming this is a volatile pair
            cbbtc_amount_wei,                      # amountADesired
            usdc_amount_wei,                       # amountBDesired
            cbbtc_min_amount,                      # amountAMin
            usdc_min_amount,                       # amountBMin
            account.address,                       # to
            deadline                               # deadline
        ).build_transaction({
            'from': account.address,
            'nonce': web3.eth.get_transaction_count(account.address),
            'gas': 500000,  # Appropriate gas limit for LP operations
            'gasPrice': web3.eth.gas_price,
        })
        
        # Sign and send transaction
        signed_tx = account.sign_transaction(tx)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for transaction receipt
        logger.info(f"Add liquidity transaction sent. Waiting for confirmation...")
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status != 1:
            logger.error(f"Add liquidity transaction failed. Transaction hash: {tx_hash.hex()}")
            return None
        
        # Parse the transaction logs to get the LP tokens received
        # This is a simplified version and might need adjustment based on the actual event structure
        lp_amount = 0  # This should be extracted from the receipt events in a real implementation
        
        return {
            "status": "success",
            "transaction_hash": tx_hash.hex(),
            "cbbtc_amount": cbbtc_amount,
            "usdc_amount": usdc_amount,
            "lp_amount": lp_amount
        }
    
    except Exception as e:
        logger.error(f"Error adding liquidity: {e}")
        return None

def stake_lp_tokens_in_gauge(lp_amount: int) -> Optional[str]:
    """
    Stake LP tokens in the cbBTC-USDC gauge to earn rewards
    
    Args:
        lp_amount: Amount of LP tokens to stake (in wei)
        
    Returns:
        Transaction hash if successful, None otherwise
    """
    try:
        account = get_account()
        pool_contract = get_contract(POOL_ADDRESS, POOL_ABI)
        gauge_contract = get_contract(GAUGE_ADDRESS, GAUGE_ABI)
        
        # Check LP token balance
        # This is a simplified approach - in a real implementation, 
        # you would need to check the actual LP token address and balance
        
        # First approve the gauge to spend LP tokens
        logger.info(f"Approving gauge to spend LP tokens")
        
        # We'd need the LP token address - for now using the pool as a placeholder
        # In reality, we'd need to get the actual LP token address
        lp_token_address = POOL_ADDRESS  # This is a simplification
        
        approve_tx = pool_contract.functions.approve(
            GAUGE_ADDRESS,
            lp_amount
        ).build_transaction({
            'from': account.address,
            'nonce': web3.eth.get_transaction_count(account.address),
            'gas': 100000,
            'gasPrice': web3.eth.gas_price,
        })
        
        # Sign and send transaction
        signed_tx = account.sign_transaction(approve_tx)
        approve_tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for approval transaction receipt
        approve_receipt = web3.eth.wait_for_transaction_receipt(approve_tx_hash)
        
        if approve_receipt.status != 1:
            logger.error("Failed to approve LP token spending")
            return None
        
        # Now stake LP tokens in the gauge
        logger.info(f"Staking {lp_amount / (10**LP_TOKEN_DECIMALS)} LP tokens in the gauge")
        
        stake_tx = gauge_contract.functions.deposit(
            lp_amount
        ).build_transaction({
            'from': account.address,
            'nonce': web3.eth.get_transaction_count(account.address),
            'gas': 200000,
            'gasPrice': web3.eth.gas_price,
        })
        
        # Sign and send transaction
        signed_tx = account.sign_transaction(stake_tx)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for transaction receipt
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status != 1:
            logger.error(f"Stake transaction failed. Transaction hash: {tx_hash.hex()}")
            return None
        
        logger.info(f"Successfully staked LP tokens. Transaction hash: {tx_hash.hex()}")
        return tx_hash.hex()
        
    except Exception as e:
        logger.error(f"Error staking LP tokens: {e}")
        return None

def claim_rewards() -> Optional[str]:
    """
    Claim earned rewards from the gauge
    
    Returns:
        Transaction hash if successful, None otherwise
    """
    try:
        account = get_account()
        gauge_contract = get_contract(GAUGE_ADDRESS, GAUGE_ABI)
        
        # Check if there are rewards to claim
        earned_amount = gauge_contract.functions.earned(account.address).call()
        
        if earned_amount == 0:
            logger.info("No rewards to claim")
            return None
        
        logger.info(f"Claiming {earned_amount / (10**18)} AERO rewards")
        
        # Execute getReward function
        claim_tx = gauge_contract.functions.getReward().build_transaction({
            'from': account.address,
            'nonce': web3.eth.get_transaction_count(account.address),
            'gas': 200000,
            'gasPrice': web3.eth.gas_price,
        })
        
        # Sign and send transaction
        signed_tx = account.sign_transaction(claim_tx)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for transaction receipt
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status != 1:
            logger.error(f"Claim rewards transaction failed. Transaction hash: {tx_hash.hex()}")
            return None
        
        logger.info(f"Successfully claimed rewards. Transaction hash: {tx_hash.hex()}")
        return tx_hash.hex()
        
    except Exception as e:
        logger.error(f"Error claiming rewards: {e}")
        return None

def get_staked_lp_balance() -> float:
    """
    Get the amount of LP tokens staked in the gauge
    
    Returns:
        Amount of staked LP tokens
    """
    try:
        account = get_account()
        gauge_contract = get_contract(GAUGE_ADDRESS, GAUGE_ABI)
        
        staked_balance = gauge_contract.functions.balanceOf(account.address).call()
        
        return staked_balance / (10**LP_TOKEN_DECIMALS)
        
    except Exception as e:
        logger.error(f"Error getting staked LP balance: {e}")
        return 0

def get_earned_rewards() -> float:
    """
    Get the amount of rewards earned but not yet claimed
    
    Returns:
        Amount of earned rewards
    """
    try:
        account = get_account()
        gauge_contract = get_contract(GAUGE_ADDRESS, GAUGE_ABI)
        
        earned_amount = gauge_contract.functions.earned(account.address).call()
        
        return earned_amount / (10**18)  # AERO token has 18 decimals
        
    except Exception as e:
        logger.error(f"Error getting earned rewards: {e}")
        return 0

def unstake_lp_tokens(amount: int) -> Optional[str]:
    """
    Unstake LP tokens from the gauge
    
    Args:
        amount: Amount of LP tokens to unstake (in wei)
        
    Returns:
        Transaction hash if successful, None otherwise
    """
    try:
        account = get_account()
        gauge_contract = get_contract(GAUGE_ADDRESS, GAUGE_ABI)
        
        # Check staked balance
        staked_balance = gauge_contract.functions.balanceOf(account.address).call()
        
        if staked_balance < amount:
            logger.error(f"Insufficient staked LP balance. Have: {staked_balance / (10**LP_TOKEN_DECIMALS)}, Trying to unstake: {amount / (10**LP_TOKEN_DECIMALS)}")
            return None
        
        logger.info(f"Unstaking {amount / (10**LP_TOKEN_DECIMALS)} LP tokens from the gauge")
        
        # Execute withdraw function
        unstake_tx = gauge_contract.functions.withdraw(
            amount
        ).build_transaction({
            'from': account.address,
            'nonce': web3.eth.get_transaction_count(account.address),
            'gas': 200000,
            'gasPrice': web3.eth.gas_price,
        })
        
        # Sign and send transaction
        signed_tx = account.sign_transaction(unstake_tx)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for transaction receipt
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status != 1:
            logger.error(f"Unstake transaction failed. Transaction hash: {tx_hash.hex()}")
            return None
        
        logger.info(f"Successfully unstaked LP tokens. Transaction hash: {tx_hash.hex()}")
        return tx_hash.hex()
        
    except Exception as e:
        logger.error(f"Error unstaking LP tokens: {e}")
        return None

def get_pool_statistics() -> Dict[str, Any]:
    """
    Get statistics about the cbBTC-USDC pool
    
    Returns:
        Dictionary with pool statistics
    """
    try:
        pool_contract = get_contract(POOL_ADDRESS, POOL_ABI)
        gauge_contract = get_contract(GAUGE_ADDRESS, GAUGE_ABI)
        
        # Get pool tokens
        token0 = pool_contract.functions.token0().call()
        token1 = pool_contract.functions.token1().call()
        
        # Get total liquidity
        total_liquidity = pool_contract.functions.liquidity().call()
        
        # Get fee tier
        fee = pool_contract.functions.fee().call()
        
        # Get total staked in gauge
        total_staked = gauge_contract.functions.totalSupply().call()
        
        # Get reward rate
        reward_rate = gauge_contract.functions.rewardRate().call()
        
        # Calculate APR (simplified)
        # This would require additional calculations based on reward token price,
        # total value locked, etc.
        estimated_apr = 0  # Placeholder
        
        return {
            "token0": token0,
            "token1": token1,
            "total_liquidity": total_liquidity / (10**LP_TOKEN_DECIMALS),
            "fee_tier": fee / 10000,  # Convert to percentage (e.g. 3000 -> 0.3%)
            "total_staked": total_staked / (10**LP_TOKEN_DECIMALS),
            "reward_rate": reward_rate / (10**18),  # AERO per second
            "estimated_apr": estimated_apr
        }
        
    except Exception as e:
        logger.error(f"Error getting pool statistics: {e}")
        return {
            "error": str(e)
        }