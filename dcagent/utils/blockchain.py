from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
import os
from typing import Optional, Dict, Any

from dcagent.config import BASE_RPC_URL, BASE_CHAIN_ID, PRIVATE_KEY

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

def approve_token_spending(token_address, spender_address, amount, gas_price=None):
    """Approve token spending"""
    account = get_account()
    token_contract = get_contract(token_address, ERC20_ABI)
    decimals = token_contract.functions.decimals().call()
    amount_in_wei = int(amount * (10 ** decimals))
    
    # Build transaction
    tx = token_contract.functions.approve(
        Web3.to_checksum_address(spender_address),
        amount_in_wei
    ).build_transaction({
        'from': account.address,
        'nonce': web3.eth.get_transaction_count(account.address),
        'gasPrice': gas_price or web3.eth.gas_price,
    })
    
    # Sign and send transaction
    signed_tx = account.sign_transaction(tx)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    
    # Wait for transaction receipt
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt