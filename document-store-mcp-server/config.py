"""Document Store MCP Server Configuration"""
import os
from pathlib import Path

# Server Configuration
SERVER_PORT = int(os.getenv("DOCUMENT_STORE_PORT", "3070"))
SERVER_HOST = os.getenv("DOCUMENT_STORE_HOST", "0.0.0.0")
TRANSPORT_TYPE = os.getenv("DOCUMENT_STORE_TRANSPORT", "streamable-http")

# Storage Configuration - use base project path
STORAGE_BASE = Path(os.getenv("DOCUMENT_STORAGE_PATH", str(Path(__file__).resolve().parent / "data")))
INGESTED_DIR = STORAGE_BASE / "ingested"

# Ensure directories exist
INGESTED_DIR.mkdir(parents=True, exist_ok=True)

# Registry Configuration (base project uses port 3031)
ENABLE_REGISTRY = os.getenv("DOCUMENT_STORE_ENABLE_REGISTRY", "true").lower() == "true"
REGISTER_WITH_REGISTRY = os.getenv("DOCUMENT_STORE_REGISTER_WITH_REGISTRY", "true").lower() == "true"
REGISTRY_HOST = os.getenv("REGISTRY_HOST", "127.0.0.1")
REGISTRY_PORT = int(os.getenv("REGISTRY_PORT", "3031"))  # base project registry port

# Performance Limits
MAX_DOCUMENT_SIZE_MB = int(os.getenv("MAX_DOCUMENT_SIZE_MB", "50"))
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "100"))
SEARCH_RESULTS_LIMIT = int(os.getenv("SEARCH_RESULTS_LIMIT", "50"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(Path(__file__).resolve().parent / "document_store.log"))
