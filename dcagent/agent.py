import time
import logging
from typing import List, Optional
from coinbase_agentkit import AgentKit

from dcagent.config import validate_config
from dcagent.strategies.base_strategy import BaseStrategy
from dcagent.strategies.dca_strategy import DCAStrategy
from dcagent.strategies.dip_strategy import DipBuyingStrategy
from dcagent.strategies.yield_strategy import YieldOptimizationStrategy
from dcagent.utils.agent_kit import initialize_agent_kit
from dcagent.action_providers.aerodrome_provider import aerodrome_action_provider

logger = logging.getLogger(__name__)

class DCAgent:
    """
    Autonomous Bitcoin DCA Agent that stacks BTC on Base using cbBTC
    """
    
    def __init__(self):
        self.strategies: List[BaseStrategy] = []
        self.running = False
        self.initialized = False
        self.agent_kit: Optional[AgentKit] = None
    
    def initialize(self) -> bool:
        """Initialize the agent and its strategies"""
        # Validate configuration
        if not validate_config():
            logger.error("Invalid configuration, agent cannot start")
            return False
        
        logger.info("Initializing DCAgent...")
        
        # Initialize AgentKit with Base integration
        try:
            self.agent_kit = initialize_agent_kit()
            
            # Add custom Aerodrome action provider
            self.agent_kit.add_action_provider(aerodrome_action_provider())
            
            logger.info("AgentKit initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AgentKit: {e}")
            return False
        
        # Initialize strategies
        self.strategies = [
            DCAStrategy(),  # Remove the agent_kit parameter
            DipBuyingStrategy(),
            YieldOptimizationStrategy()
        ]
        
        self.initialized = True
        logger.info("DCAgent initialization complete")
        return True
    
    def run(self):
        """Run the agent main loop"""
        if not self.initialized and not self.initialize():
            logger.error("Failed to initialize agent")
            return
        
        self.running = True
        logger.info("DCAgent started")
        
        try:
            while self.running:
                for strategy in self.strategies:
                    if strategy.should_execute():
                        strategy.execute()
                
                # Sleep to avoid excessive CPU usage
                time.sleep(60)  # Check every minute
        
        except KeyboardInterrupt:
            logger.info("Agent stopped by user")
        except Exception as e:
            logger.error(f"Error in agent main loop: {e}")
        finally:
            self.running = False
            logger.info("DCAgent stopped")