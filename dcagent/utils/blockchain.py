from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
import os
import time
import logging
import random
from typing import Optional, Dict, Any, TypeVar, Callable, Tuple, List
from web3.exceptions import TransactionNotFound, TimeExhausted

from dcagent.config import BASE_RPC_URL, BASE_CHAIN_ID, PRIVATE_KEY

logger = logging.getLogger(__name__)

# Initialize web3 connection to Base
web3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Check connection
if not web3.is_connected():
    raise ConnectionError(f"Failed to connect to Base L2 at {BASE_RPC_URL}")

# Standard ERC20 ABI for token interactions
ERC20_ABI = json.loads('''
[
    {
        "constant": true,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": false,
        "inputs": [{"name": "spender", "type": "address"}, {"name": "value", "type": "uint256"}],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": false,
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": false,
        "inputs": [{"name": "to", "type": "address"}, {"name": "value", "type": "uint256"}],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": false,
        "stateMutability": "nonpayable",
        "type": "function"
    }
]
''')

def get_account():
    """Get the account from private key"""
    return web3.eth.account.from_key(PRIVATE_KEY)

def get_contract(contract_address, abi):
    """Get a contract instance"""
    return web3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)

def get_token_balance(token_address, address):
    """Get token balance for an address"""
    token_contract = get_contract(token_address, ERC20_ABI)
    balance = token_contract.functions.balanceOf(Web3.to_checksum_address(address)).call()
    decimals = token_contract.functions.decimals().call()
    return balance / (10 ** decimals)

# Type variable for generic return type
T = TypeVar('T')

# Common transaction errors that might be resolved by retrying
RETRY_ERRORS = (
    "nonce too low",
    "replacement transaction underpriced",
    "transaction underpriced",
    "gas price too low",
    "already known",
    "insufficient funds",
    "known transaction",
    "execution reverted",
    "handle request error"
)

def with_retry(
    function: Callable[..., T], 
    max_retries: int = 3,
    initial_delay: float = 1, 
    backoff_factor: float = 2,
    jitter: float = 0.1,
    retry_errors: Tuple[str, ...] = RETRY_ERRORS
) -> T:
    """
    Execute a function with automatic retries on failures.
    
    Args:
        function: The function to execute with retry logic
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for the delay on each retry
        jitter: Random jitter factor to add to the delay
        retry_errors: Tuple of error message substrings that should trigger a retry
        
    Returns:
        The return value of the function if successful
        
    Raises:
        The last exception if all retries fail
    """
    last_exception = None
    delay = initial_delay
    
    # Loop through retry attempts
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.info(f"Retry attempt {attempt}/{max_retries}...")
                
            return function()
            
        except Exception as e:
            last_exception = e
            error_message = str(e).lower()
            
            # Only retry on specific errors
            retry_matched = any(err in error_message for err in retry_errors)
            if not retry_matched:
                logger.error(f"Non-retryable error: {e}")
                raise
                
            if attempt >= max_retries:
                logger.error(f"Max retries ({max_retries}) reached. Last error: {e}")
                raise
                
            # Calculate backoff delay with jitter
            jitter_amount = random.uniform(-jitter, jitter) * delay
            actual_delay = delay + jitter_amount
            logger.warning(f"Transaction failed: {e}. Retrying in {actual_delay:.2f} seconds...")
            
            time.sleep(actual_delay)
            delay *= backoff_factor
            
            # For nonce issues, update the nonce when retrying
            if "nonce" in error_message:
                logger.info("Nonce error detected, will use updated nonce on retry")
    
    # This should never be reached due to the raises above, but just in case
    raise last_exception if last_exception else RuntimeError("Retry logic failed with no exception")

def send_transaction_with_retry(
    build_tx_func: Callable[[], Dict[str, Any]],
    account: Any,
    max_retries: int = 3,
    gas_price_bump_percent: int = 10
) -> Dict[str, Any]:
    """
    Send a transaction with retry logic, automatically handling common issues like nonce and gas price.
    
    Args:
        build_tx_func: Function that builds and returns the transaction dict
        account: Web3 account to sign with
        max_retries: Maximum number of retry attempts
        gas_price_bump_percent: Percentage to bump gas price on retries
        
    Returns:
        Transaction receipt if successful
    """
    attempt = 0
    last_error = None
    gas_price_multiplier = 1.0
    
    while attempt <= max_retries:
        try:
            if attempt > 0:
                logger.info(f"Transaction retry attempt {attempt}/{max_retries}...")
            
            # Build transaction with current parameters
            tx = build_tx_func()
            
            # If not the first attempt, update nonce and gas price
            if attempt > 0:
                # Update nonce in case it changed
                tx['nonce'] = web3.eth.get_transaction_count(account.address)
                
                # Increase gas price to help the transaction go through
                if 'gasPrice' in tx:
                    tx['gasPrice'] = int(tx['gasPrice'] * gas_price_multiplier)
                    logger.info(f"Bumped gas price to {web3.from_wei(tx['gasPrice'], 'gwei'):.2f} Gwei")
                elif 'maxFeePerGas' in tx:
                    # For EIP-1559 transactions
                    tx['maxFeePerGas'] = int(tx['maxFeePerGas'] * gas_price_multiplier)
                    tx['maxPriorityFeePerGas'] = int(tx['maxPriorityFeePerGas'] * gas_price_multiplier)
            
            # Sign and send transaction
            signed_tx = account.sign_transaction(tx)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for transaction receipt with separate retry logic for waiting
            try:
                receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                logger.info(f"Transaction successful: {tx_hash.hex()}")
                return receipt
            except TimeExhausted:
                # The transaction was sent but confirmation is taking longer than expected
                logger.warning(f"Transaction sent but waiting for confirmation timed out: {tx_hash.hex()}")
                try:
                    # Try once more with a longer timeout
                    receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
                    logger.info(f"Transaction confirmed after extended wait: {tx_hash.hex()}")
                    return receipt
                except Exception as e:
                    logger.error(f"Error confirming transaction: {e}")
                    last_error = e
                    # Continue to retry
        
        except Exception as e:
            last_error = e
            logger.warning(f"Transaction failed: {e}")
            
            # Special handling for known error types
            error_message = str(e).lower()
            
            # Check if this is a retryable error
            if not any(err in error_message for err in RETRY_ERRORS):
                logger.error(f"Non-retryable error: {e}")
                raise
        
        # Increase attempt counter and gas price multiplier
        attempt += 1
        gas_price_multiplier = 1.0 + (gas_price_bump_percent / 100) * attempt
        
        # Add a small delay before retrying
        if attempt <= max_retries:
            delay = 2 ** attempt  # Exponential backoff: 2, 4, 8, 16...
            logger.info(f"Waiting {delay} seconds before retry...")
            time.sleep(delay)
    
    # If we've exhausted all retries, raise the last error
    raise last_error if last_error else RuntimeError("Transaction failed after all retries")

def approve_token_spending(token_address, spender_address, amount, gas_price=None):
    """
    Approve token spending with automatic retry logic
    
    Args:
        token_address: Address of the token contract
        spender_address: Address to approve for spending
        amount: Amount to approve (in token units, not wei)
        gas_price: Optional gas price to use
        
    Returns:
        Transaction receipt if successful
    """
    account = get_account()
    token_contract = get_contract(token_address, ERC20_ABI)
    
    # Get token decimals
    decimals = token_contract.functions.decimals().call()
    amount_in_wei = int(amount * (10 ** decimals))
    
    # Define a function to build the transaction
    def build_approve_tx():
        return token_contract.functions.approve(
            Web3.to_checksum_address(spender_address),
            amount_in_wei
        ).build_transaction({
            'from': account.address,
            'nonce': web3.eth.get_transaction_count(account.address),
            'gasPrice': gas_price or web3.eth.gas_price,
        })
    
    # Execute with retry logic
    logger.info(f"Approving {amount} tokens for spending by {spender_address}")
    receipt = send_transaction_with_retry(build_approve_tx, account)
    
    if receipt and receipt.status == 1:
        logger.info(f"Token approval successful. Transaction hash: {receipt.transactionHash.hex()}")
    else:
        logger.error(f"Token approval failed. Receipt: {receipt}")
        
    return receipt

def send_contract_transaction(
    contract_function,
    account=None,
    gas_limit=None,
    gas_price=None,
    max_retries=3,
    gas_price_bump_percent=10
) -> Dict[str, Any]:
    """
    Sends a contract transaction with retry logic
    
    Args:
        contract_function: The contract function to call
        account: The account to use (defaults to get_account())
        gas_limit: Optional gas limit to use
        gas_price: Optional gas price to use
        max_retries: Maximum number of retry attempts
        gas_price_bump_percent: Percentage to bump gas price on retries
        
    Returns:
        Transaction receipt if successful
    """
    if account is None:
        account = get_account()
    
    # Define a function to build the transaction
    def build_tx():
        tx_params = {
            'from': account.address,
            'nonce': web3.eth.get_transaction_count(account.address),
        }
        
        if gas_price is not None:
            tx_params['gasPrice'] = gas_price
        else:
            tx_params['gasPrice'] = web3.eth.gas_price
            
        if gas_limit is not None:
            tx_params['gas'] = gas_limit
            
        return contract_function.build_transaction(tx_params)
    
    # Execute with retry logic
    logger.info(f"Sending contract transaction: {contract_function.fn_name}")
    receipt = send_transaction_with_retry(build_tx, account, max_retries, gas_price_bump_percent)
    
    if receipt and receipt.status == 1:
        logger.info(f"Transaction successful. Hash: {receipt.transactionHash.hex()}")
    else:
        logger.error(f"Transaction failed. Receipt: {receipt}")
        
    return receipt