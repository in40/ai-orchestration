# Multi-Computer Network Configuration Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Network: 192.168.51.0/24                                   │
│                                                             │
│  ┌──────────────────┐     ┌──────────────────┐            │
│  │  Git Server      │     │  Web UI Server   │            │
│  │  192.168.51.187  │     │  192.168.51.X    │            │
│  │                  │     │                  │            │
│  │  mcp-results.git │     │  Web UI Backend  │            │
│  │  (code storage)  │◄────│  (port 8000)     │            │
│  │                  │ SSH │  (port 5173 FE)  │            │
│  └──────────────────┘     └──────────────────┘            │
│           │                       │                        │
│           └───────────────────────┘                        │
│                   │                                        │
│         ┌─────────┴─────────┐                             │
│         │  User Computers   │                             │
│         │  192.168.51.*     │                             │
│         └───────────────────┘                             │
└─────────────────────────────────────────────────────────────┘
```

## Server Configuration

### 1. Git Server (192.168.51.187)

**Location**: Where code is stored
**Access**: SSH from Web UI server
**Repository**: `/home/sorokin/mcp-results`

**SSH Access**:
```bash
ssh sorokin@192.168.51.187
cd /home/sorokin/mcp-results
```

**Optional - Enable HTTP Access** (if you want direct web access to Git):
```bash
# On Git server, install gitweb or cgit
sudo apt install gitweb
# Configure to serve /home/sorokin/mcp-results
```

### 2. Web UI Server

**Location**: Where Web UI backend runs
**Access**: HTTP from user computers
**Ports**: 8000 (backend), 5173 (frontend dev)

**Configuration**:
```bash
# Edit /root/qwen/base/it-lead-mcp-server/web-ui/backend/.env
WEB_UI_HOST=0.0.0.0
WEB_UI_PORT=8000
IT_LEAD_HOST=127.0.0.1
IT_LEAD_PORT=3061
```

**Start Servers**:
```bash
# Backend
cd /root/qwen/base/it-lead-mcp-server/web-ui/backend
python main.py

# Frontend (in another terminal)
cd /root/qwen/base/it-lead-mcp-server/web-ui/frontend
npm run dev -- --host 0.0.0.0
```

### 3. User Access

**From any computer on 192.168.51.x network**:

1. **Access Web UI**:
   ```
   http://192.168.51.X:5173
   ```
   (Replace X with Web UI server's IP)

2. **View Generated Code**:
   - Click green "View Result" button on completed tasks
   - Opens: `http://192.168.51.X:8000/api/git/files/{task_id}/result.py`

3. **Direct Git Access** (if needed):
   ```bash
   # Clone repository
   git clone ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git
   
   # Or view specific file
   ssh sorokin@192.168.51.187 "cat /home/sorokin/mcp-results/results/{task_id}/result.py"
   ```

## Link Types Explained

### 1. SSH Git URL (Stored in Database)
```
ssh://sorokin@192.168.51.187/home/sorokin/mcp-results/tree/main/results/{task_id}/result.py
```
- Used for Git operations
- Not directly accessible from browser
- Requires SSH authentication

### 2. Web UI HTTP Proxy
```
http://192.168.51.X:8000/api/git/files/{task_id}/result.py
```
- ✅ Works from any computer
- ✅ No SSH required
- ✅ Proper content-type (HTML renders, Python shows)
- ⚠️ Requires Web UI backend to be running

### 3. Direct Git Server HTTP (If Enabled)
```
http://192.168.51.187/results/{task_id}/result.py
```
- ✅ Direct access (no proxy)
- ⚠️ Requires Git server HTTP configuration
- ⚠️ Currently NOT configured

## Firewall Configuration

**On Web UI Server**:
```bash
# Allow HTTP access
sudo ufw allow 5173/tcp  # Frontend
sudo ufw allow 8000/tcp  # Backend
```

**On Git Server**:
```bash
# Allow SSH from Web UI server
sudo ufw allow from 192.168.51.X to any port 22
```

## Testing

### From User Computer

```bash
# 1. Test Web UI accessibility
curl http://192.168.51.X:5173

# 2. Test backend API
curl http://192.168.51.X:8000/api/tasks

# 3. Test Git file access
curl http://192.168.51.X:8000/api/git/files/{task_id}/result.py

# 4. Test SSH to Git server
ssh sorokin@192.168.51.187 "ls /home/sorokin/mcp-results/results/"
```

## Troubleshooting

### "View Result" button doesn't work

1. **Check Web UI backend is running**:
   ```bash
   ps aux | grep "python main.py"
   ```

2. **Check port 8000 is accessible**:
   ```bash
   netstat -tlnp | grep 8000
   ```

3. **Check firewall**:
   ```bash
   sudo ufw status
   ```

### Can't access from other computers

1. **Verify Web UI server IP**:
   ```bash
   ip addr show | grep "inet "
   ```

2. **Update frontend to use correct host**:
   ```bash
   cd /root/qwen/base/it-lead-mcp-server/web-ui/frontend
   npm run dev -- --host 0.0.0.0
   ```

3. **Check firewall allows external access**:
   ```bash
   sudo ufw allow 5173/tcp
   sudo ufw allow 8000/tcp
   ```

## Security Notes

⚠️ **Current Setup**:
- No authentication on HTTP endpoints
- Anyone on network can view generated code
- SSH requires authentication

🔒 **Recommendations**:
1. Add authentication to Web UI
2. Use HTTPS in production
3. Restrict Git server SSH access
4. Consider VPN for remote access

## Quick Reference

| Component | Address | Port | Purpose |
|-----------|---------|------|---------|
| Git Server | 192.168.51.187 | 22 | SSH Git access |
| Web UI Backend | 192.168.51.X | 8000 | API & file proxy |
| Web UI Frontend | 192.168.51.X | 5173 | User interface |
| IT Lead Server | 127.0.0.1 | 3061 | Task routing |
| PostgreSQL | 127.0.0.1 | 5432 | Task registry |

Replace `X` with your Web UI server's actual IP address.
