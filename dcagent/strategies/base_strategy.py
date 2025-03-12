from abc import ABC, abstractmethod
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """
    Base class for all strategies used by DCAgent
    """
    
    def __init__(self, name: str):
        self.name = name
        self.initialized = False
        self.last_execution = None
        self.next_execution = None
        logger.info(f"Initializing {name} strategy")
    
    @abstractmethod
    def should_execute(self) -> bool:
        """
        Determine if the strategy should execute now
        
        Returns:
            bool: True if the strategy should execute, False otherwise
        """
        pass
    
    @abstractmethod
    def execute(self) -> bool:
        """
        Execute the strategy
        
        Returns:
            bool: True if execution was successful, False otherwise
        """
        pass
    
    def log_execution(self, success: bool):
        """
        Log the execution result
        
        Args:
            success: Whether the execution was successful
        """
        self.last_execution = datetime.now()
        if success:
            logger.info(f"{self.name} strategy executed successfully")
        else:
            logger.error(f"{self.name} strategy execution failed")