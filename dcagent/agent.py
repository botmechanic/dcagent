import time
from typing import List, Optional
import logging

from dcagent.config import validate_config
from dcagent.strategies.base_strategy import BaseStrategy
from dcagent.strategies.dca_strategy import DCAStrategy
from dcagent.strategies.dip_strategy import DipBuyingStrategy

logger = logging.getLogger(__name__)

class DCAgent:
    """
    Autonomous Bitcoin DCA Agent that stacks BTC on Base using cbBTC
    """
    
    def __init__(self):
        self.strategies: List[BaseStrategy] = []
        self.running = False
        self.initialized = False
    
    def initialize(self) -> bool:
        """Initialize the agent and its strategies"""
        # Validate configuration
        if not validate_config():
            logger.error("Invalid configuration, agent cannot start")
            return False
        
        logger.info("Initializing DCAgent...")
        
        # Initialize strategies
        self.strategies = [
            DCAStrategy(),
            DipBuyingStrategy()
        ]
        
        self.initialized = True
        logger.info("DCAgent initialization complete")
        return True
    
    def add_strategy(self, strategy: BaseStrategy) -> None:
        """Add a strategy to the agent"""
        self.strategies.append(strategy)
        logger.info(f"Added strategy: {strategy.name}")
    
    def run(self, run_once: bool = False) -> None:
        """Run the agent, executing all strategies"""
        if not self.initialized:
            if not self.initialize():
                logger.error("Failed to initialize agent")
                return
        
        self.running = True
        logger.info("DCAgent is running...")
        
        try:
            while self.running:
                for strategy in self.strategies:
                    if strategy.should_execute():
                        logger.info(f"Executing strategy: {strategy.name}")
                        try:
                            strategy.execute()
                        except Exception as e:
                            logger.error(f"Error executing strategy {strategy.name}: {e}")
                
                if run_once:
                    self.running = False
                    break
                    
                time.sleep(60)  # Check strategies every minute
        
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            self.stop()
    
    def stop(self) -> None:
        """Stop the agent"""
        self.running = False
        logger.info("DCAgent stopped")