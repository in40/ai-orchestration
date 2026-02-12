"""Main entry point for MCP Explorer."""
import asyncio
import sys
from .tui import MCPExplorerApp


def main():
    """Run the MCP Explorer TUI application."""
    app = MCPExplorerApp()
    try:
        app.run()
    except KeyboardInterrupt:
        print("\nExiting MCP Explorer...")
        sys.exit(0)


if __name__ == "__main__":
    main()