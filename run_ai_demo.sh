#!/bin/bash

# Run the AI Advisor demo script
echo "Starting DCAgent AI Advisor Demo..."

# Check for demo mode flag
if [ "$DEMO_MODE" = "true" ]; then
    echo "Running in DEMO MODE (no API calls will be made)"
    python -m dcagent.demo_ai_advisor
    exit 0
fi

# Check if ANTHROPIC_API_KEY is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: ANTHROPIC_API_KEY environment variable is not set."
    echo "Please set it before running this script:"
    echo "export ANTHROPIC_API_KEY=your_api_key_here"
    echo ""
    echo "Or run in demo mode with:"
    echo "DEMO_MODE=true ./run_ai_demo.sh"
    exit 1
fi

# Try to install required packages, but don't fail if it doesn't work
echo "Installing necessary packages..."
pip install anthropic requests || {
    echo "WARNING: Could not install packages. If you encounter errors, try running:"
    echo "pip install anthropic requests"
    echo "or run in demo mode: DEMO_MODE=true ./run_ai_demo.sh"
}

# Run the demo script
echo "Running demo with live API..."
python -m dcagent.demo_ai_advisor