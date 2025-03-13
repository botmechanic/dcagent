# DCAgent: Autonomous BTC Stacking Agent

DCAgent is an AI-powered autonomous agent that helps users stack Bitcoin through dollar-cost averaging (DCA) on Base using cbBTC.

## Core Features

- **Automated DCA**: Schedule regular BTC purchases at fixed intervals
- **Intelligent Dip Buying**: Automatically detect and buy price dips
- **Gas Optimization**: AI-powered transaction timing to minimize gas costs
- **Yield Maximization**: Automatically stake and earn yield on your BTC holdings
- **Analytics Dashboard**: Track performance and get AI-generated insights

## Tech Stack

- Python 3.10+
- AgentKit for autonomous agent capabilities
- Base blockchain for low-cost transactions
- cbBTC as the trusted BTC wrapper token
- Web3.py for blockchain interactions

## Getting Started

### Prerequisites
- Python 3.10+
- Poetry (for dependency management)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/botmechanic/dc-agent.git
   cd dc-agent
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Create a `.env` file with your configuration:
   ```
   BASE_RPC_URL=https://mainnet.base.org
   BASE_CHAIN_ID=8453
   PRIVATE_KEY=your_private_key_here
   DCA_AMOUNT=50
   DCA_INTERVAL=weekly
   ENABLE_DIP_BUYING=true
   ENABLE_YIELD_OPTIMIZATION=true
   ```

### Running DCAgent

#### Run Agent Only
```bash
poetry run python -m dcagent.main
```

#### Run Agent with Dashboard
```bash
poetry run ./run_dcagent.sh
# or directly:
poetry run streamlit run dashboard.py
```

The dashboard will be available at http://localhost:8501

## Dashboard Features

The DCAgent dashboard provides a comprehensive visualization of your DCA agent's performance:

- **Overview**: See your current balances, BTC price, and portfolio growth
- **Performance**: Track DCA and dip buying performance with detailed metrics
- **Transactions**: Monitor all transactions with filtering by type and date
- **Logs**: View system logs with filtering by log level

The dashboard also allows you to manually trigger actions like DCA execution and reward claiming.

## Development Status

This project is currently under active development for the Ethereum SF Hackathon.
