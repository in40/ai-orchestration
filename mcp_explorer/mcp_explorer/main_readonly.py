"""Main entry point for MCP Explorer (Read-Only)."""
import asyncio
import sys
from .tui_readonly import MCPExplorerReadOnlyApp


def main():
    """Run the MCP Explorer TUI application in read-only mode."""
    app = MCPExplorerReadOnlyApp(expand_all_by_default=True)  # Set to True to expand all by default
    try:
        app.run()
    except KeyboardInterrupt:
        print("\nExiting MCP Explorer (Read-Only)...")
        sys.exit(0)


if __name__ == "__main__":
    main()