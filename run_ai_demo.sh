#!/bin/bash

# Run the AI Advisor demo script
echo "Starting DCAgent AI Advisor Demo..."

# Check if ANTHROPIC_API_KEY is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: ANTHROPIC_API_KEY environment variable is not set."
    echo "Please set it before running this script:"
    echo "export ANTHROPIC_API_KEY=your_api_key_here"
    exit 1
fi

# Run the demo script
poetry run python -m dcagent.demo_ai_advisor