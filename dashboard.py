import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time, random
from datetime import datetime, timedelta
import json
import os
import threading
import sys

# Flag to run in demo mode (without backend agent dependencies)
DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"

try:
    from dcagent.config import (
        DCA_AMOUNT, 
        DCA_INTERVAL, 
        ENABLE_DIP_BUYING, 
        ENABLE_YIELD_OPTIMIZATION,
        CBBTC_CONTRACT_ADDRESS, 
        USDC_CONTRACT_ADDRESS
    )
    if not DEMO_MODE:
        from dcagent.utils.pyth_utils import get_btc_price, get_price_with_confidence
        from dcagent.utils.blockchain import get_account, get_token_balance
        from dcagent.utils.aerodrome import get_earned_rewards, get_staked_lp_balance, get_pool_statistics
except ImportError as e:
    # If we can't import the modules, assume demo mode
    DEMO_MODE = True
    print(f"Running in demo mode due to import error: {e}")
    
    # Set default values for demo mode
    DCA_AMOUNT = 50
    DCA_INTERVAL = "weekly"
    ENABLE_DIP_BUYING = True
    ENABLE_YIELD_OPTIMIZATION = True
    CBBTC_CONTRACT_ADDRESS = "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf"
    USDC_CONTRACT_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# Initialize global variables for storing state
if 'price_history' not in st.session_state:
    st.session_state.price_history = []
if 'transaction_history' not in st.session_state:
    st.session_state.transaction_history = []
if 'logs' not in st.session_state:
    st.session_state.logs = []

# Custom log handler to capture logs for display in the UI
class StreamlitLogHandler:
    def __init__(self):
        self.logs = []

    def emit(self, record):
        log_entry = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'level': record.levelname,
            'message': record.getMessage()
        }
        self.logs.append(log_entry)
        # Keep only the last 100 logs
        if len(self.logs) > 100:
            self.logs = self.logs[-100:]
        st.session_state.logs = self.logs

# Get current data (real or demo)
def get_current_data():
    if DEMO_MODE:
        # In demo mode, use simulated data with current price range
        btc_price = 80500 + random.uniform(-500, 500)  # Simulate BTC price around $80.5K
        cbbtc_balance = 0.0125  # Simulated cbBTC balance
        usdc_balance = 250.75   # Simulated USDC balance
        
        # Set price source and confidence for demo mode
        confidence = btc_price * 0.005  # 0.5% confidence interval
        confidence_pct = 0.5
        price_source = "Coinbase (Demo)"
        
        # Simulate yield data
        staked_lp = 0.0023 if ENABLE_YIELD_OPTIMIZATION else 0
        earned_rewards = 0.15 if ENABLE_YIELD_OPTIMIZATION else 0
    else:
        # In real mode, fetch actual data
        try:
            account = get_account()
            # Get BTC price and confidence interval
            price_data = get_price_with_confidence()
            if price_data:
                btc_price, confidence = price_data
                price_source = "Coinbase" if confidence == btc_price * 0.005 else "Pyth"
                confidence_pct = (confidence / btc_price) * 100
            else:
                btc_price = 65000
                confidence = 325  # 0.5% default
                confidence_pct = 0.5
                price_source = "Fallback"
                
            cbbtc_balance = get_token_balance(CBBTC_CONTRACT_ADDRESS, account.address)
            usdc_balance = get_token_balance(USDC_CONTRACT_ADDRESS, account.address)
            
            # Fetch yield data if enabled
            staked_lp = 0
            earned_rewards = 0
            if ENABLE_YIELD_OPTIMIZATION:
                staked_lp = get_staked_lp_balance()
                earned_rewards = get_earned_rewards()
        except Exception as e:
            # Fallback to demo data if there's an error
            st.error(f"Error fetching data: {e}. Using simulated data.")
            btc_price = 65000
            confidence = 325  # 0.5% default
            confidence_pct = 0.5
            price_source = "Fallback"
            cbbtc_balance = 0.01
            usdc_balance = 200
            staked_lp = 0.002 if ENABLE_YIELD_OPTIMIZATION else 0
            earned_rewards = 0.1 if ENABLE_YIELD_OPTIMIZATION else 0
    
    # For demo mode, set default confidence and source
    if DEMO_MODE:
        confidence = btc_price * 0.005  # 0.5% of price
        confidence_pct = 0.5
        price_source = "Coinbase (Demo)"
        
    return {
        'timestamp': datetime.now(),
        'btc_price': btc_price,
        'confidence': confidence,
        'confidence_pct': confidence_pct,
        'price_source': price_source,
        'cbbtc_balance': cbbtc_balance,
        'usdc_balance': usdc_balance,
        'staked_lp': staked_lp,
        'earned_rewards': earned_rewards
    }

# Function to update price history
def update_price_history():
    current_data = get_current_data()
    st.session_state.price_history.append({
        'timestamp': current_data['timestamp'],
        'price': current_data['btc_price'],
        'confidence': current_data['confidence'],
        'price_source': current_data['price_source']
    })
    # Keep only the last 24 hours of data
    if len(st.session_state.price_history) > 144:  # 144 * 10 minutes = 24 hours
        st.session_state.price_history = st.session_state.price_history[-144:]

# Load events from events.json
def load_events():
    """Load events from events.json"""
    events_file = "events.json"
    if os.path.exists(events_file):
        with open(events_file, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

# Main dashboard app
def main():
    st.set_page_config(
        page_title="DCAgent Dashboard", 
        page_icon="📈", 
        layout="wide", 
        initial_sidebar_state="expanded"
    )
    
    # Create sidebar
    st.sidebar.title("DCAgent Control Panel")
    st.sidebar.info("Autonomous Bitcoin DCA Agent")
    
    # Configuration section
    st.sidebar.header("Configuration")
    st.sidebar.text(f"DCA Amount: ${DCA_AMOUNT}")
    st.sidebar.text(f"DCA Interval: {DCA_INTERVAL}")
    st.sidebar.text(f"Dip Buying: {'Enabled' if ENABLE_DIP_BUYING else 'Disabled'}")
    st.sidebar.text(f"Yield Optimization: {'Enabled' if ENABLE_YIELD_OPTIMIZATION else 'Disabled'}")
    
    # Add manual controls
    st.sidebar.header("Manual Controls")
    if st.sidebar.button("Execute DCA Now"):
        st.sidebar.success("DCA execution triggered!")
        # Here you'd add code to trigger the DCA strategy manually
    
    if ENABLE_DIP_BUYING and st.sidebar.button("Simulate Dip Buy"):
        st.sidebar.success("Dip buy simulation triggered!")
        # Here you'd add code to simulate a dip buy
    
    if ENABLE_YIELD_OPTIMIZATION and st.sidebar.button("Claim Rewards"):
        st.sidebar.success("Reward claim triggered!")
        # Here you'd add code to claim rewards
    
    # Main content area with tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Performance", "Transactions", "AI Insights", "Logs"])
    
    # Update data for real-time display
    update_price_history()
    current_data = get_current_data()
    
    # Tab 1: Overview
    with tab1:
        st.header("Portfolio Overview")
        
        # Create metrics at the top
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label=f"BTC Price ({current_data['price_source']})", 
                value=f"${current_data['btc_price']:,.2f}",
                delta=f"{(current_data['btc_price'] - 65000)/65000:.2%}" if current_data['btc_price'] else None
            )
            st.caption(f"± ${current_data['confidence']:,.2f} ({current_data['confidence_pct']:.2f}%)")
        
        with col2:
            st.metric(
                label="cbBTC Balance", 
                value=f"{current_data['cbbtc_balance']:.6f}"
            )
        
        with col3:
            st.metric(
                label="USDC Balance", 
                value=f"${current_data['usdc_balance']:,.2f}"
            )
            
        with col4:
            if current_data['cbbtc_balance'] > 0:
                portfolio_value = current_data['cbbtc_balance'] * current_data['btc_price']
                st.metric(
                    label="Portfolio Value", 
                    value=f"${portfolio_value:,.2f}"
                )
            else:
                st.metric(
                    label="Portfolio Value", 
                    value="$0.00"
                )
        
        # BTC price chart with confidence interval
        st.subheader("BTC Price Chart")
        if st.session_state.price_history:
            df = pd.DataFrame(st.session_state.price_history)
            
            # Create figure
            fig = go.Figure()
            
            # Add BTC price line
            fig.add_trace(go.Scatter(
                x=df['timestamp'], 
                y=df['price'],
                mode='lines',
                name='BTC Price',
                line=dict(color='#F7931A', width=2),
                hovertemplate='%{y:$,.2f}<br>Source: %{text}<extra></extra>',
                text=df['price_source']
            ))
            
            # Add hover data showing price source
            hover_data = []
            for _, row in df.iterrows():
                hover_data.append(f"Source: {row['price_source']}<br>± ${row['confidence']:,.2f}")
            
            # Add a custom annotation showing the price source
            last_price = df['price'].iloc[-1]
            last_time = df['timestamp'].iloc[-1]
            last_source = df['price_source'].iloc[-1]
            
            fig.add_annotation(
                x=last_time,
                y=last_price,
                text=f"Source: {last_source}",
                showarrow=True,
                arrowhead=1,
                ax=50,
                ay=-40
            )
            
            # Update layout
            fig.update_layout(
                height=400,
                xaxis_title="Time",
                yaxis_title="Price (USD)",
                hovermode="x unified",
                margin=dict(l=0, r=0, t=10, b=0)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Show a note about the price source
            st.caption(f"Current price source: {current_data['price_source']} (± ${current_data['confidence']:,.2f}, {current_data['confidence_pct']:.2f}% confidence)")
        else:
            st.info("Waiting for price data...")
        
        # Portfolio Growth Chart
        st.subheader("Portfolio Growth")
        # Simulated portfolio growth (replace with actual data)
        dates = [datetime.now() - timedelta(days=i*7) for i in range(12)]
        portfolio_values = [500 + (i * 50) for i in range(12)]

        df = pd.DataFrame({
            'Date': dates,
            'Value': portfolio_values
        })

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['Date'], 
            y=df['Value'],
            mode='lines+markers',
            name='Portfolio Value',
            fill='tozeroy',
            line=dict(color='purple', width=2)
        ))
        fig.update_layout(
            height=300,
            xaxis_title="Date",
            yaxis_title="Portfolio Value (USD)",
            margin=dict(l=0, r=0, t=10, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # If yield optimization is enabled, show yield section
        if ENABLE_YIELD_OPTIMIZATION:
            st.subheader("Yield Farming Position")
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    label="Staked LP Tokens", 
                    value=f"{current_data['staked_lp']:.6f}"
                )
            with col2:
                st.metric(
                    label="Earned AERO Rewards", 
                    value=f"{current_data['earned_rewards']:.6f}"
                )
    
    # Tab 2: Performance
    with tab2:
        st.header("Performance Metrics")
        
        # Example performance metrics
        col1, col2 = st.columns(2)
        
        with col1:
            # DCA Performance
            st.subheader("DCA Performance")
            
            # Get DCA events
            dca_events = [e for e in load_events() if e.get("type") == "dca_execution"]
            dca_count = len(dca_events)
            
            if dca_count > 0:
                # Calculate actual performance metrics
                total_invested = dca_count * DCA_AMOUNT
                
                # Calculate average BTC price during DCA purchases
                btc_prices = [e.get("data", {}).get("btc_price", 0) for e in dca_events]
                avg_btc_price = sum(btc_prices) / len(btc_prices) if btc_prices else 0
                
                # Calculate performance vs current price
                current_price = current_data['btc_price']
                performance = ((current_price - avg_btc_price) / avg_btc_price * 100) if avg_btc_price else 0
                
                dca_performance = {
                    'DCA Count': dca_count,
                    'Total Invested': f"${total_invested:.2f}",
                    'Average BTC Price': f"${avg_btc_price:,.2f}",
                    'Current BTC Price': f"${current_price:,.2f}",
                    'Performance': f"{performance:+.2f}%"
                }
            else:
                # Use placeholder data if no events
                dca_performance = {
                    'DCA Count': 0,
                    'Total Invested': f"$0.00",
                    'Average BTC Price': "N/A",
                    'Current BTC Price': f"${current_data['btc_price']:,.2f}",
                    'Performance': "N/A"
                }
            
            for key, value in dca_performance.items():
                st.text(f"{key}: {value}")
            
            # Show a historical chart of DCA executions
            st.subheader("DCA Execution History")
            # Placeholder chart - replace with actual data
            dates = [datetime.now() - timedelta(days=i*7) for i in range(12)]
            prices = [60000 + (i * 500) for i in range(12)]
            
            df = pd.DataFrame({
                'Date': dates,
                'BTC Price': prices
            })
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df['Date'], 
                y=df['BTC Price'],
                mode='markers',
                name='DCA Purchases',
                marker=dict(size=10, color='green')
            ))
            fig.update_layout(
                height=300,
                xaxis_title="Date",
                yaxis_title="BTC Price at Purchase (USD)",
                margin=dict(l=0, r=0, t=10, b=0)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Dip Buying Performance (if enabled)
            if ENABLE_DIP_BUYING:
                st.subheader("Dip Buying Performance")
                
                # Simulated dip buying performance (replace with actual data)
                dip_performance = {
                    'Dips Detected': 3,
                    'Dips Bought': 2,
                    'Total Invested': f"${2 * DCA_AMOUNT:.2f}",
                    'Average BTC Price': "$61,245.32",
                    'Current BTC Price': f"${current_data['btc_price']:,.2f}",
                    'Performance': "+12.1%"
                }
                
                for key, value in dip_performance.items():
                    st.text(f"{key}: {value}")
                
                # Show a chart of dip detections
                st.subheader("Dip Detection History")
                
                # Load dip detection events
                dip_events = [e for e in load_events() if e.get("type") == "dip_detected"]
                
                if dip_events:
                    # Format data for the chart
                    dates = []
                    prices = []
                    types = []
                    percentages = []
                    
                    for event in dip_events:
                        data = event.get("data", {})
                        
                        # Parse timestamp
                        timestamp = event.get("timestamp", "")
                        if timestamp:
                            try:
                                dates.append(datetime.fromisoformat(timestamp))
                            except ValueError:
                                dates.append(datetime.now())
                        else:
                            dates.append(datetime.now())
                        
                        # Get price and status
                        prices.append(data.get("btc_price", 0))
                        status = data.get("status", "")
                        types.append("Detected & Bought" if status == "bought" else "Detected Only")
                        percentages.append(data.get("dip_percentage", 0))
                    
                    df = pd.DataFrame({
                        'Date': dates,
                        'Type': types,
                        'Price': prices,
                        'Percentage': percentages
                    })
                else:
                    # Use placeholder data if no events
                    df = pd.DataFrame({
                        'Date': [datetime.now() - timedelta(days=d) for d in [5, 12, 20]],
                        'Type': ['Detected & Bought', 'Detected & Bought', 'Detected Only'],
                        'Price': [58000, 57500, 59200],
                        'Percentage': [5.2, 6.1, 4.8]
                    })
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df['Date'], 
                    y=df['Price'],
                    mode='markers',
                    name='Dips',
                    marker=dict(
                        size=12, 
                        color=['green', 'green', 'orange']
                    )
                ))
                fig.update_layout(
                    height=300,
                    xaxis_title="Date",
                    yaxis_title="BTC Price (USD)",
                    margin=dict(l=0, r=0, t=10, b=0)
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Yield Performance (if enabled)
            if ENABLE_YIELD_OPTIMIZATION:
                st.subheader("Yield Performance")
                
                # Simulated yield performance (replace with actual data)
                yield_performance = {
                    'Total Staked Value': "$345.67",
                    'Earned Rewards': "$12.45",
                    'APR': "8.2%",
                    'Time Staked': "24 days"
                }
                
                for key, value in yield_performance.items():
                    st.text(f"{key}: {value}")
                    
        # BTC Price with Moving Averages and Confidence
        st.subheader("BTC Price with Moving Averages")
        if len(st.session_state.price_history) > 24:
            df = pd.DataFrame(st.session_state.price_history)
            df['MA_6h'] = df['price'].rolling(window=6).mean()
            df['MA_24h'] = df['price'].rolling(window=24).mean()
            
            # Add current confidence interval to the chart
            confidence = current_data['confidence']
            upper_bound = current_data['btc_price'] + confidence
            lower_bound = current_data['btc_price'] - confidence
            
            fig = go.Figure()
            
            # Add confidence interval as a shaded area at the right edge of the chart
            latest_time = df['timestamp'].iloc[-1]
            
            # Create a confidence band for the latest price
            fig.add_trace(go.Scatter(
                x=[latest_time, latest_time],
                y=[lower_bound, upper_bound],
                mode='lines',
                line=dict(color='rgba(200, 200, 200, 0.5)', width=10),
                name=f'Price Confidence ({current_data["confidence_pct"]:.2f}%)'
            ))
            
            # Add main price line
            fig.add_trace(go.Scatter(
                x=df['timestamp'], 
                y=df['price'],
                mode='lines',
                name=f'BTC Price ({current_data["price_source"]})',
                line=dict(color='#F7931A', width=2)
            ))
            
            # Add moving averages
            fig.add_trace(go.Scatter(
                x=df['timestamp'], 
                y=df['MA_6h'],
                mode='lines',
                name='6-Hour MA',
                line=dict(color='blue', width=1.5)
            ))
            fig.add_trace(go.Scatter(
                x=df['timestamp'], 
                y=df['MA_24h'],
                mode='lines',
                name='24-Hour MA',
                line=dict(color='green', width=1.5)
            ))
            
            fig.update_layout(
                height=400,
                xaxis_title="Time",
                yaxis_title="Price (USD)",
                hovermode="x unified",
                margin=dict(l=0, r=0, t=10, b=0)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Need at least 24 data points for moving averages")
    
    # Tab 3: Transactions
    with tab3:
        st.header("Transaction History")
        
        # Add filter options
        col1, col2 = st.columns(2)
        with col1:
            transaction_type = st.selectbox(
                "Filter by type:",
                ["All", "DCA Buy", "Dip Buy", "Add Liquidity", "Stake LP", "Claim Rewards"]
            )
        
        with col2:
            date_range = st.selectbox(
                "Filter by date:",
                ["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days"]
            )
        
        # Load transactions from events.json
        events = load_events()
        
        # Filter for transaction events
        transaction_events = [e for e in events if e.get("type") == "transaction"]
        
        # Convert to the format expected by the UI
        transactions = []
        for event in transaction_events:
            data = event.get("data", {})
            details = data.get("details", {})
            tx_type = data.get("type", "Unknown")
            amount = details.get("amount", 0)
            token = details.get("token", "")
            
            # Format timestamp
            timestamp = event.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass
            
            transactions.append({
                "timestamp": timestamp,
                "type": tx_type,
                "amount": f"{amount:.8f} {token}" if tx_type != "DCA Buy" else f"${details.get('usdc_amount', 0):.2f}",
                "status": details.get("status", "Success"),
                "tx_hash": details.get("tx_hash", "")
            })
        
        # Apply filters
        if transaction_type != "All":
            transactions = [t for t in transactions if t["type"] == transaction_type]
        
        if date_range != "All Time":
            # Apply date filter based on selection
            pass
        
        # Display transactions
        if transactions:
            for tx in transactions:
                with st.expander(f"{tx['timestamp']} - {tx['type']} - {tx['amount']}"):
                    st.text(f"Status: {tx['status']}")
                    st.text(f"Transaction Hash: {tx['tx_hash']}")
                    st.markdown(f"[View on BaseScan](https://basescan.org/tx/{tx['tx_hash']})")
        else:
            st.info("No transactions found matching your filters.")
    
    # Tab 4: AI Insights
    with tab4:
        st.header("AI Strategy Insights")
        
        with st.container():
            st.subheader("Current Market Analysis")
            
            # This would normally come from your events.json, using placeholder for demo
            ai_events = [e for e in load_events() if "ai_sentiment" in e.get("data", {})]
            latest_ai_event = ai_events[-1] if ai_events else None
            
            if latest_ai_event:
                data = latest_ai_event.get("data", {})
                
                # Display sentiment with appropriate color
                sentiment = data.get("ai_sentiment", "neutral")
                sentiment_color = {
                    "bullish": "green",
                    "bearish": "red", 
                    "neutral": "blue"
                }.get(sentiment, "blue")
                
                st.markdown(f"<h3 style='color:{sentiment_color}'>Market Sentiment: {sentiment.title()}</h3>", unsafe_allow_html=True)
                
                # Display AI reasoning
                st.markdown("### AI Analysis")
                st.write(data.get("ai_reasoning", "No analysis available"))
                
                # Display AI insight
                if "ai_insight" in data:
                    st.markdown("### Strategic Insight")
                    st.info(data.get("ai_insight"))
                    
            else:
                st.info("No AI insights available yet. The agent will generate insights as it executes strategies.")
            
            # Add a button to request a new analysis
            if st.button("Request New Analysis"):
                st.success("Analysis requested. The agent will update the insights on the next execution cycle.")
                
        # Add AI price prediction section
        st.subheader("🔮 AI Market Prediction")
        
        def get_ai_prediction():
            """Get AI prediction for future BTC price"""
            
            # This would normally use your ClaudeAdvisor, but we'll simulate for the demo
            if DEMO_MODE:
                current_price = get_current_data()['btc_price']
                # Simulate a prediction with some random variation
                prediction = {
                    "price_7d": current_price * (1 + random.uniform(-0.05, 0.15)),
                    "price_30d": current_price * (1 + random.uniform(0, 0.25)),
                    "confidence": random.uniform(0.65, 0.85),
                    "reasoning": "Based on current market conditions and historical patterns, BTC appears to be in an accumulation phase with strong support around $78,000. Technical indicators suggest potential upward momentum over the next 30 days, though short-term volatility may continue.",
                    "recommendation": "Continue regular DCA with possible increase in position size during significant dips below $76,000."
                }
                return prediction
            else:
                # In real mode, you would use the Claude API
                try:
                    from dcagent.utils.claude_advisor import ClaudeAdvisor
                    advisor = ClaudeAdvisor()
                    # Get data for prediction
                    price = get_current_data()['btc_price']
                    # Hard code price history for example
                    history = [price * (1 + ((i - 10) * 0.005)) for i in range(20)]
                    
                    analysis = advisor.market_analysis(price, history)
                    
                    # Format as prediction
                    prediction = {
                        "price_7d": price * (1 + (0.05 if analysis['sentiment'] == 'bullish' else -0.05)),
                        "price_30d": price * (1 + (0.15 if analysis['sentiment'] == 'bullish' else -0.10)),
                        "confidence": 0.75,
                        "reasoning": analysis['reasoning'],
                        "recommendation": analysis['strategy_recommendation']
                    }
                    return prediction
                except Exception as e:
                    st.error(f"Error getting AI prediction: {e}")
                    return None
        
        prediction = get_ai_prediction()
        if prediction:
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    label="Predicted Price (7 days)", 
                    value=f"${prediction['price_7d']:,.2f}",
                    delta=f"{((prediction['price_7d'] - current_data['btc_price']) / current_data['btc_price'] * 100):.1f}%"
                )
            with col2:
                st.metric(
                    label="Predicted Price (30 days)", 
                    value=f"${prediction['price_30d']:,.2f}",
                    delta=f"{((prediction['price_30d'] - current_data['btc_price']) / current_data['btc_price'] * 100):.1f}%"
                )
            
            st.progress(prediction['confidence'], text=f"Confidence: {prediction['confidence']:.0%}")
            
            st.subheader("AI Reasoning")
            st.write(prediction['reasoning'])
            
            st.subheader("Recommendation")
            st.info(prediction['recommendation'])
        else:
            st.info("No AI prediction available at this time.")
    
    # Tab 5: Logs
    with tab5:
        st.header("System Logs")
        
        # Log level filter
        log_level = st.selectbox(
            "Filter by level:",
            ["All", "INFO", "WARNING", "ERROR", "DEBUG"]
        )
        
        # Display logs
        if st.session_state.logs:
            filtered_logs = st.session_state.logs
            if log_level != "All":
                filtered_logs = [log for log in filtered_logs if log['level'] == log_level]
            
            for log in reversed(filtered_logs):
                color = {
                    "INFO": "blue",
                    "WARNING": "orange",
                    "ERROR": "red",
                    "DEBUG": "green"
                }.get(log['level'], "black")
                
                st.markdown(f"<span style='color:{color}'>[{log['timestamp']}] [{log['level']}] {log['message']}</span>", unsafe_allow_html=True)
        else:
            st.info("No logs available yet.")

if __name__ == "__main__":
    main()