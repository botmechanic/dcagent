import logging
import os
from typing import Any, Dict, Optional

from coinbase_agentkit import AgentKit
from coinbase_agentkit.action_providers import (
    wallet_action_provider,
    erc20_action_provider
)
from coinbase_agentkit.wallet_providers import (
    EvmWalletProviderConfig,
    eth_account_wallet_provider
)

from dcagent.config import BASE_RPC_URL, BASE_CHAIN_ID, PRIVATE_KEY

logger = logging.getLogger(__name__)

def initialize_agent_kit() -> AgentKit:
    """Initialize AgentKit with Base L2 configuration"""
    
    # Configure wallet provider for Base L2
    wallet_config = EvmWalletProviderConfig(
        rpc_url=BASE_RPC_URL,
        chain_id=int(BASE_CHAIN_ID),
        private_key=PRIVATE_KEY,
    )
    
    # Create wallet provider
    wallet_provider = eth_account_wallet_provider(wallet_config)
    
    # Initialize AgentKit with wallet provider
    agent_kit = AgentKit(
        wallet_provider=wallet_provider,
        action_providers=[
            wallet_action_provider(),
            erc20_action_provider(),
            # Add additional action providers as needed
        ]
    )
    
    return agent_kit

def get_wallet_details() -> Dict[str, Any]:
    """Get wallet details using AgentKit"""
    agent_kit = initialize_agent_kit()
    
    # Get wallet details action
    get_wallet_action = agent_kit.get_action("wallet_get_wallet_details")
    wallet_details = get_wallet_action.execute({})
    
    return wallet_details

def get_token_balance(token_address: str, wallet_address: Optional[str] = None) -> int:
    """Get token balance using AgentKit"""
    agent_kit = initialize_agent_kit()
    
    # Get balance action
    get_balance_action = agent_kit.get_action("erc20_get_balance")
    balance_result = get_balance_action.execute({"contract_address": token_address})
    
    # Parse the result (AgentKit usually returns formatted strings)
    try:
        # Extract the numerical value from the result string
        balance_parts = balance_result.split(" is ")
        if len(balance_parts) > 1:
            balance = float(balance_parts[1])
            # Convert to Wei based on token decimals
            # This is a simplification - proper implementation would check token decimals
            return int(balance * 10**18)
        return 0
    except Exception as e:
        logger.error(f"Error parsing balance result: {e}")
        return 0

def transfer_tokens(token_address: str, to_address: str, amount: int) -> Optional[str]:
    """Transfer tokens using AgentKit"""
    agent_kit = initialize_agent_kit()
    
    # Get transfer action
    transfer_action = agent_kit.get_action("erc20_transfer")
    
    try:
        result = transfer_action.execute({
            "contract_address": token_address,
            "destination": to_address,
            "amount": str(amount)
        })
        
        # Parse transaction hash from result
        # This assumes the result contains the transaction hash
        if "Transaction hash" in result:
            tx_hash = result.split("Transaction hash")[1].strip().strip(':').strip()
            return tx_hash
        return None
    except Exception as e:
        logger.error(f"Error transferring tokens: {e}")
        return None