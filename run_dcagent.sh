#!/bin/bash

# Start the DCAgent in a separate process
echo "Starting DCAgent..."
python -m dcagent.main &
AGENT_PID=$!

# Start the Streamlit dashboard
echo "Starting Dashboard..."
streamlit run dashboard.py

# When the dashboard is closed, kill the agent process
kill $AGENT_PID