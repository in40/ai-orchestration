# MCP Systemd Services

This directory contains systemd unit files for managing all MCP services as system services.

## Overview

The MCP system consists of 8 services that can be managed individually or together:

| Service | Port | Description |
|---------|------|-------------|
| `mcp-registry` | 3031 | Service discovery and registry |
| `mcp-implementation-engineer` | 3060 | Code generation |
| `mcp-requirements-engineer` | 3062 | Requirements analysis |
| `mcp-it-lead` | 3061 | Task routing and planning |
| `mcp-team-management` | 3063 | Team coordination |
| `mcp-devops-release-engineer` | 3071 | Deployment automation |
| `mcp-web-ui-backend` | 8000 | FastAPI backend |
| `mcp-web-ui-frontend` | 5173 | Vite frontend |

## Installation

### Prerequisites

- Linux system with systemd
- Root/sudo access
- PostgreSQL running (for services that use it)
- `.env` file configured at `/root/qwen/base/.env`

### Install Services

```bash
# Install all systemd service files
sudo ./install_systemd_services.sh

# Or manually:
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
```

## Usage

### Start/Stop/Restart All Services

```bash
# Start all services (via master - pulls in all dependencies)
sudo systemctl start mcp-master

# Stop all services
sudo systemctl stop mcp-master

# Restart all services
sudo systemctl restart mcp-master

# Check status of all services
sudo systemctl status mcp-master
```

### Individual Service Control

```bash
# Start/stop individual services
sudo systemctl start mcp-registry
sudo systemctl stop mcp-registry
sudo systemctl restart mcp-registry
sudo systemctl status mcp-registry
```

### View Logs

```bash
# View logs for a service
sudo journalctl -u mcp-registry -n 50

# Follow logs in real-time
sudo journalctl -u mcp-registry -f

# Filter by service
sudo journalctl -u mcp-it-lead -f
```

### Enable/Disable on Boot

```bash
# Enable services to start on boot
sudo systemctl enable mcp-master

# Disable services from starting on boot
sudo systemctl disable mcp-master

# Enable/disable individual service
sudo systemctl enable mcp-registry
sudo systemctl disable mcp-registry
```

### Check Service Status

```bash
# List all MCP services with status
systemctl list-units --type=service --all | grep mcp

# Check specific service
systemctl is-active mcp-registry
systemctl is-enabled mcp-master
```

## Service Dependencies

Services start in the following order:

```
postgresql.service (optional)
    ↓
mcp-registry.service (3031)
    ↓
├── mcp-implementation-engineer.service (3060)
├── mcp-requirements-engineer.service (3062)
├── mcp-it-lead.service (3061)
│   └── mcp-web-ui-backend.service (8000)
│       └── mcp-web-ui-frontend.service (5173)
├── mcp-team-management.service (3063)
└── mcp-devops-release-engineer.service (3071)
```

## Configuration

All services read configuration from `/root/qwen/base/.env`. Key settings:

```bash
# Network
REGISTRY_HOST=127.0.0.1
REGISTRY_PORT=3031
WEB_UI_HOST=0.0.0.0

# PostgreSQL
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=mcp_registry
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
USE_POSTGRES=true

# LLM
LLM_PROVIDER_URL=http://192.168.51.237:1234/v1/chat/completions
LLM_MODEL=qwen3.5-35b-a3b@q5_k_xl
```

## Logging

All services log to systemd journal. View logs with:

```bash
# Recent logs
sudo journalctl -u mcp-registry -n 50

# Follow in real-time
sudo journalctl -u mcp-registry -f

# Since boot
sudo journalctl -u mcp-registry -b

# Since specific time
sudo journalctl -u mcp-registry --since "1 hour ago"
```

## Uninstall

```bash
# Using the management script
sudo ./mcp-service.sh uninstall

# Or manually
sudo systemctl stop mcp-master
sudo systemctl disable mcp-master
sudo rm /etc/systemd/system/mcp-*.service
sudo systemctl daemon-reload
```

## Troubleshooting

### Service won't start

```bash
# Check service status
sudo systemctl status mcp-registry

# View detailed logs
sudo journalctl -u mcp-registry -n 100 --no-pager

# Check if port is in use
ss -tlnp | grep 3031

# Check .env file exists and is readable
cat /root/qwen/base/.env
```

### Service keeps restarting

```bash
# Check restart attempts
sudo systemctl status mcp-registry

# View recent error logs
sudo journalctl -u mcp-registry -p err --no-pager
```

### Port conflicts

```bash
# Find process using port
sudo lsof -i :3031

# Kill conflicting process
sudo kill -9 <PID>
```

## Migration from Old Scripts

If you were using `start_mcp_master.sh` and `stop_mcp_master.sh`:

1. Stop old processes:
   ```bash
   sudo ./stop_mcp_master.sh
   ```

2. Install systemd services:
   ```bash
   sudo ./install_systemd_services.sh
   ```

3. Start services:
   ```bash
   sudo systemctl start mcp-master
   ```

4. (Optional) Enable on boot:
   ```bash
   sudo systemctl enable mcp-master
   ```

## Security Notes

- Services run as root (can be changed in unit files)
- PostgreSQL password should be changed from default
- Consider using a dedicated system user for MCP services
- Firewall rules should restrict access to service ports
