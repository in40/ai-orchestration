# MCP System Configuration Guide

This guide explains how to configure the MCP Orchestration System using the centralized configuration system.

## Quick Start

### 1. Copy Configuration Template

```bash
cd /root/qwen/base
cp .env.example .env
```

### 2. Edit Configuration

```bash
nano .env
# or
vim .env
```

### 3. Update Key Settings

**For Single Computer (localhost):**
```env
WEB_UI_HOST=127.0.0.1
WEB_UI_PUBLIC_URL=http://localhost:8000
```

**For Network Access:**
```env
WEB_UI_HOST=0.0.0.0
WEB_UI_PUBLIC_URL=http://YOUR_SERVER_IP:8000
```

### 4. Start System

```bash
bash start_mcp_master.sh
```

## Configuration File Structure

### Files

- **`.env`** - Your actual configuration (gitignored, customize here)
- **`.env.example`** - Template with documentation (committed to git)
- **`config.py`** - Configuration management module

### Settings Categories

1. **Network Configuration** - Network domain
2. **Server Ports** - Port numbers for all services
3. **Server Hosts** - Host addresses for network access
4. **PostgreSQL Database** - Database connection settings
5. **LLM Configuration** - LLM server URL and model
6. **Git Repository** - Git server and repository paths
7. **Web UI Configuration** - Public URLs for web access
8. **Performance & Limits** - Timeouts and size limits
9. **Logging** - Log level and directory
10. **Feature Flags** - Enable/disable features
11. **Paths** - Base directories

## Common Configurations

### Setup 1: Single Computer Development

All services run on localhost, no network access needed.

```env
# Server Hosts
REGISTRY_HOST=127.0.0.1
IT_LEAD_HOST=127.0.0.1
WEB_UI_HOST=127.0.0.1

# Web UI
WEB_UI_PUBLIC_URL=http://localhost:8000
WEB_UI_FRONTEND_URL=http://localhost:5173
```

### Setup 2: Server with Network Access

Web UI accessible from other computers on the network.

```env
# Server Hosts
REGISTRY_HOST=127.0.0.1
IT_LEAD_HOST=127.0.0.1
WEB_UI_HOST=0.0.0.0  # Allow network access

# Web UI (replace with your server IP)
WEB_UI_PUBLIC_URL=http://192.168.51.50:8000
WEB_UI_FRONTEND_URL=http://192.168.51.50:5173
```

### Setup 3: Multi-Server Deployment

Different services on different machines.

```env
# Point to separate servers
REGISTRY_HOST=192.168.51.10
IT_LEAD_HOST=192.168.51.11
POSTGRES_HOST=192.168.51.20

# Git server
GIT_SERVER_HOST=192.168.51.187

# Web UI
WEB_UI_HOST=0.0.0.0
WEB_UI_PUBLIC_URL=http://192.168.51.30:8000
```

### Setup 4: Docker Deployment

```env
# Use container names
POSTGRES_HOST=postgres-db
REGISTRY_HOST=registry-server

# Allow network access
WEB_UI_HOST=0.0.0.0

# Use Docker network
WEB_UI_PUBLIC_URL=http://host.docker.internal:8000
```

## Key Settings Explained

### WEB_UI_HOST

Controls who can access the Web UI:

- `127.0.0.1` - Only localhost (secure, single-computer)
- `0.0.0.0` - All network interfaces (network access)
- `192.168.51.X` - Specific interface only

### WEB_UI_PUBLIC_URL

The URL users type in their browser. Must match your server's IP:

```env
# Local access only
WEB_UI_PUBLIC_URL=http://localhost:8000

# Network access (replace with your IP)
WEB_UI_PUBLIC_URL=http://192.168.51.50:8000
```

### POSTGRES_PASSWORD

⚠️ **SECURITY**: Change the default password in production!

```env
# Default (insecure)
POSTGRES_PASSWORD=postgres

# Production (secure)
POSTGRES_PASSWORD=YourSecurePassword123!
```

### LLM_PROVIDER_URL

Points to your LLM server (LM Studio, Ollama, etc.):

```env
# LM Studio
LLM_PROVIDER_URL=http://192.168.51.237:1234/v1/chat/completions

# Ollama
LLM_PROVIDER_URL=http://localhost:11434/v1/chat/completions

# OpenAI-compatible API
LLM_PROVIDER_URL=https://api.openai.com/v1/chat/completions
```

### GIT_REPO_URL

Where generated code is stored:

```env
# SSH format
GIT_REPO_URL=ssh://user@host/path/to/repo.git

# Example
GIT_REPO_URL=ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git
```

## Environment Variable Override

You can override `.env` settings with environment variables:

```bash
# Override database password
export POSTGRES_PASSWORD=MySecurePassword

# Override LLM model
export LLM_MODEL=qwen3.5-35b-a3b@q5_k_xl

# Start server
python main.py
```

Environment variables take precedence over `.env` file.

## Testing Configuration

### Check Current Settings

```bash
cd /root/qwen/base
python config.py
```

Output:
```
MCP System Configuration
============================================================
Network Domain:        192.168.51.0/24

Server Ports:
  Registry:            3031
  IT Lead:             3061
  ...

Database:
  Host:                127.0.0.1:5432
  Database:            mcp_registry
  ...
```

### Validate Configuration

```bash
# Test database connection
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB

# Test LLM connection
curl $LLM_PROVIDER_URL -d '{"model": "$LLM_MODEL", ...}'

# Test Git access
ssh $GIT_SERVER_HOST "ls $GIT_REPO_PATH"
```

## Troubleshooting

### Web UI Not Accessible from Network

**Problem**: Can access from server but not from other computers.

**Solution**:
1. Set `WEB_UI_HOST=0.0.0.0`
2. Update `WEB_UI_PUBLIC_URL` with server IP
3. Check firewall: `sudo ufw allow 8000/tcp`
4. Restart Web UI backend

### Database Connection Failed

**Problem**: `Error connecting to PostgreSQL`

**Solution**:
1. Check `POSTGRES_HOST` is correct
2. Verify PostgreSQL is running: `sudo systemctl status postgresql`
3. Test connection: `psql -h $POSTGRES_HOST -U $POSTGRES_USER`
4. Check `pg_hba.conf` allows connections

### LLM Not Responding

**Problem**: `LLM API call failed`

**Solution**:
1. Verify `LLM_PROVIDER_URL` is correct
2. Check LLM server is running
3. Test with curl: `curl $LLM_PROVIDER_URL ...`
4. Verify model name matches: `echo $LLM_MODEL`

### Git Push Fails

**Problem**: `Failed to push to Git repository`

**Solution**:
1. Check `GIT_REPO_URL` is correct
2. Test SSH access: `ssh $GIT_SERVER_HOST`
3. Verify repository exists: `ssh $GIT_SERVER_HOST "ls $GIT_REPO_PATH"`
4. Check SSH keys are configured

## Security Best Practices

1. **Change Default Passwords**
   ```env
   POSTGRES_PASSWORD=YourSecurePassword123!
   ```

2. **Use HTTPS in Production**
   - Configure reverse proxy (nginx, Apache)
   - Use Let's Encrypt certificates

3. **Restrict Network Access**
   ```env
   # Only allow specific network interface
   WEB_UI_HOST=192.168.51.50
   ```

4. **Firewall Configuration**
   ```bash
   sudo ufw allow from 192.168.51.0/24 to any port 8000
   sudo ufw enable
   ```

5. **Keep .env Secret**
   - Never commit `.env` to git
   - Set permissions: `chmod 600 .env`

## Migration from Hardcoded Settings

If you're updating from hardcoded settings:

1. **Backup Current Setup**
   ```bash
   cp -r /root/qwen/base /root/qwen/base.backup
   ```

2. **Create .env from Current Settings**
   - Review current shell scripts
   - Extract hardcoded values
   - Add to `.env`

3. **Update Python Files**
   - Import config: `from config import get_settings`
   - Replace hardcoded values: `settings.VARIABLE_NAME`

4. **Test Thoroughly**
   - Start with single server
   - Verify all connections work
   - Test from network computers

## Complete Example

**File: `/root/qwen/base/.env`**
```env
# Network
NETWORK_DOMAIN=192.168.51.0/24

# Server Ports
REGISTRY_PORT=3031
IT_LEAD_PORT=3061
WEB_UI_BACKEND_PORT=8000
WEB_UI_FRONTEND_PORT=5173

# Server Hosts
REGISTRY_HOST=127.0.0.1
IT_LEAD_HOST=127.0.0.1
WEB_UI_HOST=0.0.0.0

# PostgreSQL
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=mcp_registry
POSTGRES_USER=postgres
POSTGRES_PASSWORD=MySecurePassword123!
USE_POSTGRES=true

# LLM
LLM_PROVIDER_URL=http://192.168.51.237:1234/v1/chat/completions
LLM_MODEL=qwen3.5-35b-a3b@q5_k_xl
LLM_TEMPERATURE=0.3

# Git
GIT_SERVER_HOST=192.168.51.187
GIT_REPO_URL=ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git
GIT_LOCAL_CLONE_PATH=/tmp/mcp-vibe-coding-git/repo

# Web UI
WEB_UI_PUBLIC_URL=http://192.168.51.50:8000
WEB_UI_FRONTEND_URL=http://192.168.51.50:5173

# Performance
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=120

# Logging
LOG_LEVEL=INFO
LOG_DIR=/tmp

# Features
ENABLE_REGISTRY=true
REGISTER_WITH_REGISTRY=true
USE_POSTGRES=true

# Paths
BASE_DIR=/root/qwen/base
DATA_DIR=/root/qwen/base/data
```

## Additional Resources

- `.env.example` - Complete template with all settings
- `config.py` - Configuration module source code
- `NETWORK_CONFIGURATION_GUIDE.md` - Network setup details
- `README.md` - General system documentation

## Support

For issues or questions:
1. Check logs: `tail -f /tmp/*.log`
2. Run config test: `python config.py`
3. Review documentation in `/root/qwen/base/docs/`
