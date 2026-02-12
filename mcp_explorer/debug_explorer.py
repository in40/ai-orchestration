#!/usr/bin/env python3
"""Debug script to run explorer with error logging."""

import asyncio
import sys
import traceback
from mcp_explorer.tui import MCPExplorerApp


def main():
    """Run the MCP Explorer TUI application with error handling."""
    app = MCPExplorerApp()
    try:
        app.run()
    except KeyboardInterrupt:
        print("\nExiting MCP Explorer...")
        sys.exit(0)
    except Exception as e:
        print(f"\nError running MCP Explorer: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()