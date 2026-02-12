#!/usr/bin/env python3
"""
Run the explorer with full exception handling to capture the exact error.
"""
import sys
import traceback
import logging
from mcp_explorer.main import main

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/mcp_explorer_error.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main_with_error_capture():
    try:
        logger.info("Starting MCP Explorer with error capture...")
        main()
    except KeyboardInterrupt:
        logger.info("Explorer interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Explorer crashed with error: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error("Full traceback:")
        logger.error(traceback.format_exc())
        print(f"\nExplorer crashed with error: {e}")
        print(f"Error type: {type(e).__name__}")
        print("Check /tmp/mcp_explorer_error.log for details")
        sys.exit(1)

if __name__ == "__main__":
    main_with_error_capture()