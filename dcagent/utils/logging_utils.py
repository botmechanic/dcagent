import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List

# Configure logger
logger = logging.getLogger(__name__)

def log_event(event_type: str, data: Dict[str, Any]) -> None:
    """
    Log an event to the events.json file for the dashboard
    
    Args:
        event_type: Type of event (e.g., "dca_execution", "dip_detection")
        data: Data associated with the event
    """
    event = {
        "timestamp": datetime.now().isoformat(),
        "type": event_type,
        "data": data
    }
    
    events_file = "events.json"
    events = []
    
    # Read existing events
    if os.path.exists(events_file):
        with open(events_file, "r") as f:
            try:
                events = json.load(f)
            except json.JSONDecodeError:
                events = []
    
    # Add new event
    events.append(event)
    
    # Write events back to file (keep only last 100)
    with open(events_file, "w") as f:
        json.dump(events[-100:], f)
    
    logger.info(f"Logged {event_type} event: {data}")

def log_transaction(
    tx_type: str,
    tx_hash: str,
    amount: float,
    token: str,
    status: str = "Success",
    additional_data: Dict[str, Any] = None
) -> None:
    """
    Log a blockchain transaction to the events.json file
    
    Args:
        tx_type: Type of transaction (e.g., "DCA Buy", "Dip Buy")
        tx_hash: Transaction hash
        amount: Amount involved in the transaction
        token: Token symbol (e.g., "BTC", "USDC")
        status: Transaction status (default: "Success")
        additional_data: Additional data to include
    """
    data = {
        "tx_hash": tx_hash,
        "amount": amount,
        "token": token,
        "status": status
    }
    
    if additional_data:
        data.update(additional_data)
    
    log_event("transaction", {
        "type": tx_type,
        "details": data
    })

def get_recent_transactions(limit: int = 10, tx_type: str = None) -> List[Dict[str, Any]]:
    """
    Get recent transactions from the events.json file
    
    Args:
        limit: Maximum number of transactions to retrieve
        tx_type: Filter by transaction type (optional)
        
    Returns:
        List of transaction events
    """
    events_file = "events.json"
    
    if not os.path.exists(events_file):
        return []
    
    try:
        with open(events_file, "r") as f:
            events = json.load(f)
    except (json.JSONDecodeError, IOError):
        return []
    
    # Filter for transaction events
    transactions = [
        event for event in events 
        if event.get("type") == "transaction"
    ]
    
    # Filter by transaction type if specified
    if tx_type:
        transactions = [
            tx for tx in transactions 
            if tx.get("data", {}).get("type") == tx_type
        ]
    
    # Sort by timestamp (newest first)
    transactions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # Limit results
    return transactions[:limit]

def get_strategy_stats(strategy_name: str) -> Dict[str, Any]:
    """
    Get statistics for a particular strategy
    
    Args:
        strategy_name: Name of the strategy (e.g., "dca", "dip")
        
    Returns:
        Dictionary with strategy statistics
    """
    events_file = "events.json"
    
    if not os.path.exists(events_file):
        return {}
    
    try:
        with open(events_file, "r") as f:
            events = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}
    
    # Filter events for this strategy
    strategy_events = [
        event for event in events 
        if event.get("data", {}).get("strategy") == strategy_name
    ]
    
    # Calculate statistics (this is a placeholder - enhance based on your needs)
    stats = {
        "execution_count": len(strategy_events),
        "last_execution": max([e.get("timestamp") for e in strategy_events], default=None),
        # Add other relevant statistics
    }
    
    return stats