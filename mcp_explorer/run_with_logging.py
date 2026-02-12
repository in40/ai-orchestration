#!/usr/bin/env python3
"""
Script to run the explorer with full error logging.
"""
import sys
import traceback
import logging
from mcp_explorer.main import main

# Set up logging to capture all errors
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def run_with_detailed_error_handling():
    """Run the explorer with comprehensive error handling."""
    try:
        print("Starting MCP Explorer with detailed error handling...", file=sys.stderr)
        main()
    except KeyboardInterrupt:
        print("\nExiting MCP Explorer...", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"\nMCP Explorer crashed with error: {e}", file=sys.stderr)
        print("\nFull traceback:", file=sys.stderr)
        traceback.print_exc()
        print("\nError type:", type(e).__name__, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_with_detailed_error_handling()