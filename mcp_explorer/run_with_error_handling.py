#!/usr/bin/env python3
"""
Script to run the explorer with enhanced error handling to catch the crash.
"""
import sys
import traceback
from mcp_explorer.tui import MCPExplorerApp

def run_explorer_with_error_handling():
    """Run the explorer with comprehensive error handling."""
    try:
        print("Starting MCP Explorer with error handling...")
        app = MCPExplorerApp(expand_all_by_default=True)
        app.run()
    except KeyboardInterrupt:
        print("\nExiting MCP Explorer...")
        sys.exit(0)
    except Exception as e:
        print(f"\nMCP Explorer crashed with error: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_explorer_with_error_handling()