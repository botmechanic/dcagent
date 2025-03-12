import logging
import sys
from dcagent.agent import DCAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('dcagent.log')
    ]
)

def main():
    """Entry point for the DC Agent application"""
    agent = DCAgent()
    agent.run()

if __name__ == "__main__":
    main()