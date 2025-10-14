# Logging Guide - MCP Document Server

## Overview

The MCP Document Server now has comprehensive logging to help debug OAuth token handling and OneDrive integration issues.

## Log Locations

### 1. Docker Container Logs (Stdout/Stderr)
Real-time logs are written to stdout/stderr and can be viewed using Docker commands.

**View live logs:**
```bash
docker logs -f mcp-document-server
```

**View last 100 lines:**
```bash
docker logs --tail 100 mcp-document-server
```

**View with timestamps:**
```bash
docker logs -t mcp-document-server
```

**Search logs for specific terms:**
```bash
docker logs mcp-document-server 2>&1 | grep "Authorization"
docker logs mcp-document-server 2>&1 | grep "Bearer"
docker logs mcp-document-server 2>&1 | grep "token"
```

### 2. Log Files (Persistent Storage)
Logs are also written to a file for easier review and archiving.

**Log file location:**
- **Inside container:** `/logs/mcp_server.log`
- **On host machine:** `./logs/mcp_server.log`

**View log file:**
```bash
# View entire log
cat ./logs/mcp_server.log

# View last 50 lines
tail -n 50 ./logs/mcp_server.log

# Follow log in real-time
tail -f ./logs/mcp_server.log

# Search for specific terms
grep "Authorization" ./logs/mcp_server.log
grep "✗" ./logs/mcp_server.log  # Find errors/warnings
grep "✓" ./logs/mcp_server.log  # Find successful operations
```

## Log Levels

The server supports different log levels via the `LOG_LEVEL` environment variable:

- **DEBUG**: Most verbose - shows all header details, token previews, context structure
- **INFO**: Standard level - shows key operations and token extraction success
- **WARNING**: Only warnings and errors
- **ERROR**: Only errors

**To change log level:**

Edit `.env` file:
```bash
LOG_LEVEL=DEBUG
```

Or set in `docker-compose.yml`:
```yaml
environment:
  - LOG_LEVEL=DEBUG
```

Then restart the container:
```bash
docker-compose restart mcp-document-server
```

## What to Look For: Bearer Token Debugging

### ✓ Successful Token Capture

When LibreChat successfully passes the token, you'll see:

```
INFO - ✓ Authorization header found: Bearer eyJ0eXAiO...B9xK2Uw
INFO - ✓ User-ID header found: 12345678...
INFO - ✓ Successfully extracted OAuth token for user: 12345678... (token length: 1456, preview: eyJ0eXAiO...B9xK2Uw)
INFO - OneDriveClient initialized for user 12345678... (token preview: eyJ0eXAiO...)
```

### ✗ Missing Authorization Header

If the Authorization header is not being passed:

```
WARNING - ✗ No Authorization header found in request
DEBUG - Available headers: content-type, user-agent, x-request-id
ERROR - Authorization header not found
```

### ✗ Empty or Malformed Token

If the header exists but is malformed:

```
WARNING - Authorization header present but doesn't start with 'Bearer ': Basic abc123...
ERROR - Invalid Authorization format: Basic abc123...
```

### ✗ No Request Context

If FastMCP is not passing the context properly:

```
ERROR - No request context available for OAuth token extraction
DEBUG - ctx=None, hasattr(ctx, 'meta')=N/A
```

## Enhanced Debug Logging Features

### 1. Header Inspection
```
DEBUG - Context meta type: <class 'dict'>
DEBUG - Context meta keys: ['headers', 'request_id']
INFO - Received 3 header(s) from request
DEBUG - Header keys (case-sensitive): ['Authorization', 'X-User-ID', 'Content-Type']
```

### 2. Token Validation
```
DEBUG - Authorization header found, length: 1463
DEBUG - Token starts with: eyJ0eXAiOiJKV1QiL...
INFO - ✓ Successfully extracted OAuth token (token length: 1456, preview: eyJ0eXAiO...B9xK2Uw)
```

### 3. Authentication Failures
```
ERROR - Authentication failed (401) for user 12345678...
DEBUG - Request URL: https://graph.microsoft.com/v1.0/me/drive/items/root/children
DEBUG - Token preview: eyJ0eXAiO...B9xK2Uw
ERROR - Microsoft API error: {'error': {'code': 'InvalidAuthenticationToken', 'message': 'Access token has expired'}}
```

## Troubleshooting Common Issues

### Issue 1: No logs appearing

**Check if container is running:**
```bash
docker ps | grep mcp-document-server
```

**Check if logs directory exists:**
```bash
ls -la ./logs/
```

**Create logs directory if missing:**
```bash
mkdir -p ./logs
docker-compose restart mcp-document-server
```

### Issue 2: Can't see DEBUG logs

**Set log level to DEBUG:**
```bash
echo "LOG_LEVEL=DEBUG" >> .env
docker-compose restart mcp-document-server
```

### Issue 3: LibreChat not passing Authorization header

Check your LibreChat MCP configuration (`.librechat_config.md`):

```yaml
headers:
  Authorization: "Bearer {{OAUTH_ACCESS_TOKEN}}"  # ✓ Correct
  X-User-ID: "{{LIBRECHAT_USER_ID}}"
```

**Look for these log patterns:**
```bash
# Check if headers are being received at all
docker logs mcp-document-server 2>&1 | grep "Received.*header"

# Check if Authorization is in the headers
docker logs mcp-document-server 2>&1 | grep "Authorization header found"

# Check what headers ARE being received
docker logs mcp-document-server 2>&1 | grep "Header keys"
```

### Issue 4: Token format issues

**Check token length:**
```bash
docker logs mcp-document-server 2>&1 | grep "token length"
```

Microsoft OAuth tokens are typically 1000-2000 characters. If you see:
- `[too short]` or `[short]` - Token is malformed
- Token length < 50 - Token is invalid
- Token doesn't start with typical patterns (e.g., `eyJ`) - May not be a JWT

## Example Debugging Session

**Step 1: Enable DEBUG logging**
```bash
echo "LOG_LEVEL=DEBUG" >> .env
docker-compose restart mcp-document-server
```

**Step 2: Make a request with OneDrive upload enabled**
```bash
# Use LibreChat to create a document with "upload_to_onedrive: true"
```

**Step 3: Review logs in real-time**
```bash
tail -f ./logs/mcp_server.log
```

**Step 4: Look for the authentication flow**
```
[timestamp] - INFO - OneDrive upload requested for path: /Documents/LibreChat
[timestamp] - DEBUG - Context meta type: <class 'dict'>
[timestamp] - DEBUG - Context meta keys: ['headers', 'request_id']
[timestamp] - INFO - Received 2 header(s) from request
[timestamp] - DEBUG - Header keys (case-sensitive): ['Authorization', 'X-User-ID']
[timestamp] - INFO - ✓ Authorization header found: Bearer eyJ0eXAiO...B9xK2Uw
[timestamp] - DEBUG - Token length: 1456 chars
[timestamp] - INFO - ✓ User-ID header found: 67890abc...
```

**Step 5: If token is missing, check what headers ARE present**
```bash
grep "Header keys" ./logs/mcp_server.log
```

## Log Rotation & Disk Space Management

### Automatic Log Rotation

To prevent logs from filling your hard drive, both Docker logs and application file logs are automatically rotated.

#### Application File Logs (./logs/mcp_server.log)

**Default Configuration:**
- **Max file size:** 10 MB per log file
- **Backup count:** 5 backup files
- **Total disk usage:** ~60 MB maximum (1 current + 5 backups)

When `mcp_server.log` reaches 10MB:
1. `mcp_server.log` → `mcp_server.log.1`
2. `mcp_server.log.1` → `mcp_server.log.2`
3. ... and so on up to `.5`
4. Oldest file (`mcp_server.log.5`) is deleted
5. New `mcp_server.log` is created

**Customize rotation settings** in `.env`:
```bash
# Maximum size per log file (in bytes)
LOG_MAX_BYTES=20971520    # 20MB

# Number of backup files to keep
LOG_BACKUP_COUNT=10       # 10 backups = 220MB total
```

#### Docker Container Logs (docker logs)

**Default Configuration:**
- **Max file size:** 10 MB per log file
- **Max files:** 3 files
- **Total disk usage:** ~30 MB maximum
- **Compression:** Enabled (rotated logs are compressed)

These are configured in [docker-compose.yml](docker-compose.yml):
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"      # Per-file size limit
    max-file: "3"        # Number of files to keep
    compress: "true"     # Compress rotated logs
```

### Total Disk Usage

With default settings:
- **Application logs:** ~60 MB (`./logs/`)
- **Docker logs:** ~30 MB (compressed)
- **Total:** ~90 MB maximum

### Checking Log File Sizes

```bash
# Check application log sizes
du -h ./logs/

# List all log files with sizes
ls -lh ./logs/

# Check Docker container logs location
docker inspect mcp-document-server | grep LogPath
```

### Manual Log Cleanup

If you need to manually clear logs:

```bash
# Clear application logs (Docker container must be stopped)
docker-compose stop mcp-document-server
rm -f ./logs/mcp_server.log*
docker-compose start mcp-document-server

# Clear Docker logs (requires root/sudo on most systems)
truncate -s 0 $(docker inspect --format='{{.LogPath}}' mcp-document-server)

# Or restart container to start fresh Docker logs
docker-compose restart mcp-document-server
```

## Performance Considerations

- **File logs** are automatically rotated (max: 60MB by default)
- **Docker logs** are automatically rotated and compressed (max: 30MB by default)
- **DEBUG logging** produces ~2-3x more log volume - use only for troubleshooting
- **Production recommendation**: Use `LOG_LEVEL=INFO`
- **High-traffic deployments**: Consider increasing `LOG_MAX_BYTES` or reducing `LOG_BACKUP_COUNT`

## Summary

With the enhanced logging in place, you now have visibility into:

1. ✓ Whether LibreChat is passing the Authorization header
2. ✓ The format and length of the token
3. ✓ Whether the token is being extracted correctly
4. ✓ Authentication failures with Microsoft Graph API
5. ✓ All headers received from LibreChat

Use `LOG_LEVEL=DEBUG` for troubleshooting, and review logs in both:
- Real-time: `docker logs -f mcp-document-server`
- File: `tail -f ./logs/mcp_server.log`
