#!/bin/bash
# Script to run the AI agent simulation tests

cd "$(dirname "$0")/.."
source venv/bin/activate
python tests/simulate_agent.py