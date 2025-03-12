import os
import logging
from typing import Any, Dict, Optional
from decimal import Decimal

from coinbase_agentkit.action_providers import ActionProvider, create_action
from coinbase_agentkit.wallet_providers import EvmWalletProvider
from pydantic import BaseModel, Field

from dcagent.utils.aerodrome import (
    add_liquidity, 
    stake_lp_tokens_in_gauge,
    claim_rewards,
    get_staked_lp_balance,
    get_earned_rewards
)

logger = logging.getLogger(__name__)

# Schema definitions
class AddLiquiditySchema(BaseModel):
    """Schema for adding liquidity to Aerodrome"""
    cbbtc_amount: str = Field(..., description="Amount of cbBTC to provide")
    usdc_amount: str = Field(..., description="Amount of USDC to provide")
    slippage: float = Field(0.01, description="Maximum slippage (default 1%)")

class StakeLPSchema(BaseModel):
    """Schema for staking LP tokens"""
    lp_amount: str = Field(..., description="Amount of LP tokens to stake")

class AerodromeActionProvider(ActionProvider[EvmWalletProvider]):
    """Action provider for Aerodrome Finance"""
    
    def __init__(self):
        super().__init__("aerodrome", [])
        
    @create_action(
        name="add_liquidity",
        description="""
        Add liquidity to the cbBTC-USDC pool on Aerodrome Finance.
        """,
        schema=AddLiquiditySchema
    )
    def add_liquidity_action(self, wallet_provider: EvmWalletProvider, args: Dict[str, Any]) -> str:
        try:
            cbbtc_amount = Decimal(args["cbbtc_amount"])
            usdc_amount = Decimal(args["usdc_amount"])
            slippage = float(args.get("slippage", 0.01))
            
            result = add_liquidity(cbbtc_amount, usdc_amount, slippage)
            
            if not result:
                return "Failed to add liquidity"
            
            return f"Successfully added liquidity: {cbbtc_amount} cbBTC and {usdc_amount} USDC"
        except Exception as e:
            return f"Error adding liquidity: {e}"
    
    @create_action(
        name="stake_lp",
        description="""
        Stake LP tokens in the cbBTC-USDC gauge to earn rewards.
        """,
        schema=StakeLPSchema
    )
    def stake_lp_action(self, wallet_provider: EvmWalletProvider, args: Dict[str, Any]) -> str:
        try:
            lp_amount = int(Decimal(args["lp_amount"]) * (10**18))  # LP tokens have 18 decimals
            
            tx_hash = stake_lp_tokens_in_gauge(lp_amount)
            
            if not tx_hash:
                return "Failed to stake LP tokens"
            
            return f"Successfully staked LP tokens. Transaction hash: {tx_hash}"
        except Exception as e:
            return f"Error staking LP tokens: {e}"
    
    @create_action(
        name="claim_rewards",
        description="""
        Claim rewards from the Aerodrome gauge.
        """
    )
    def claim_rewards_action(self, wallet_provider: EvmWalletProvider, args: Dict[str, Any]) -> str:
        try:
            tx_hash = claim_rewards()
            
            if not tx_hash:
                return "Failed to claim rewards"
            
            return f"Successfully claimed rewards. Transaction hash: {tx_hash}"
        except Exception as e:
            return f"Error claiming rewards: {e}"
    
    @create_action(
        name="get_yield_info",
        description="""
        Get information about current yield farming position.
        """
    )
    def get_yield_info_action(self, wallet_provider: EvmWalletProvider, args: Dict[str, Any]) -> str:
        try:
            staked_balance = get_staked_lp_balance()
            earned_rewards = get_earned_rewards()
            
            return (
                f"Your Aerodrome Yield Position:\n"
                f"- Staked LP tokens: {staked_balance:.6f}\n"
                f"- Earned AERO rewards: {earned_rewards:.6f}\n"
            )
        except Exception as e:
            return f"Error getting yield information: {e}"

def aerodrome_action_provider() -> AerodromeActionProvider:
    """Create a new Aerodrome action provider"""
    return AerodromeActionProvider()