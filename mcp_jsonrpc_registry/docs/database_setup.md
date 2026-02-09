# Database Setup Guide

This guide explains how to set up the PostgreSQL database for the MCP Server Registry.

## Database Requirements

The MCP Server Registry requires:
- PostgreSQL 12 or higher
- A dedicated database: `mcp_registry`
- A dedicated user: `mcp_user` with password `mcp_password`
- Proper permissions for the user on the database

## Quick Setup (Recommended)

The easiest way to set up the database is to use the initialization script:

```bash
# Make sure PostgreSQL server is running
sudo systemctl start postgresql  # On Debian/Ubuntu systems

# Run the database initialization script
./init_database.sh
```

## Manual Setup

If you prefer to set up the database manually, follow these steps:

### 1. Access PostgreSQL as Superuser

```bash
sudo -u postgres psql
```

### 2. Create the Database User

```sql
CREATE USER mcp_user WITH PASSWORD 'mcp_password';
```

### 3. Create the Database

```sql
CREATE DATABASE mcp_registry OWNER mcp_user;
```

### 4. Grant Permissions

```sql
GRANT ALL PRIVILEGES ON DATABASE mcp_registry TO mcp_user;
```

### 5. Exit PostgreSQL

```sql
\q
```

## Configuration

Once the database is set up, configure the application by updating the `.env` file:

```
DATABASE_URL=postgresql://mcp_user:mcp_password@localhost/mcp_registry
```

## Verification

To verify that the database is set up correctly, you can run the test script:

```bash
# Activate virtual environment
source venv/bin/activate

# Run the test
python test_db_connection.py
```

## Troubleshooting

### Common Issues

1. **Connection refused**: Make sure PostgreSQL is running
2. **Authentication failed**: Verify the username and password in your `.env` file
3. **Permission denied**: Ensure the user has proper permissions on the database

### Check PostgreSQL Status

```bash
sudo systemctl status postgresql
```

### Restart PostgreSQL (if needed)

```bash
sudo systemctl restart postgresql
```

## Production Considerations

For production deployments, consider:
- Using stronger passwords
- Configuring SSL/TLS for database connections
- Setting up proper backup strategies
- Configuring connection pooling
- Monitoring database performance