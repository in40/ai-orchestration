# MCP Explorer

A TUI explorer for Model Context Protocol (MCP) servers using Streamable HTTP transport.

## Features

- Midnight Commander-style interface with two-panel layout
- Streamable HTTP transport (no legacy SSE or WebSocket)
- Support for multiple registry types:
  - Default localhost:3031 registry
  - GitHub registry
  - Nacos registry  
  - Custom registry URLs
- Dynamic form generation from JSON schemas
- Tool calling with parameter validation
- Canonical naming: `<server-name>__<tool-name>`

## Installation

```bash
pip install mcp-explorer
```

## Usage

```bash
mcp-explorer
```

## Keybindings

- `Tab`: Switch focus between left (registry tree) and right (detail panel)
- `Enter`: On server - connect and fetch tools; On tool - open parameter form
- `F7`: Call tool (when form is active)
- `Ctrl+R`: Refresh current view
- `F2`: Add custom registry
- `F8`: Quit application

## Architecture

- **Transport**: Streamable HTTP only (POST/GET to single endpoint)
- **Language**: Python 3.11+
- **TUI**: textual library
- **JSON Schema Validation**: pydantic
- **HTTP Client**: httpx

## Default Registry

On first startup, MCP Explorer attempts to connect to `http://localhost:3031/mcp`.
If unavailable, a connection error panel is displayed with options to add custom registries.

## Verification

See [VERIFICATION.md](VERIFICATION.md) for detailed verification steps to ensure compliance with MCP Streamable HTTP specifications.