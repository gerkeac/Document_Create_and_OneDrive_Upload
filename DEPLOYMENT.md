# Deployment Guide

This guide covers deploying the MCP Document Generator Server to various environments.

## Table of Contents

- [Local Development](#local-development)
- [Portainer Deployment](#portainer-deployment)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

---

## Local Development

### Prerequisites
- Docker and Docker Compose installed
- Git repository cloned locally

### Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd Document_Create_and_OneDrive_Upload

# Build and start with docker-compose
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Custom Port

```bash
# Use a different port if 3000 is in use
MCP_EXTERNAL_PORT=8080 docker-compose up
```

---

## Portainer Deployment

Portainer supports multiple deployment methods. Choose the one that best fits your workflow.

### Option A: Build from Git Repository (Recommended - Easiest)

Portainer can build directly from your git repository ([see documentation](https://docs.portainer.io/user/docker/images/build)).

**Step 1: Ensure uv.lock is committed**

```bash
# Verify uv.lock is tracked in git
git ls-files | grep uv.lock

# If not found, add it
git add uv.lock
git commit -m "Add uv.lock for reproducible builds"
git push
```

**Step 2: Deploy in Portainer**

1. Open Portainer web interface
2. Navigate to **Stacks** → **Add Stack**
3. Name your stack (e.g., `mcp-document-server`)
4. Choose **Repository** method
5. Configure repository:
   - **Repository URL**: Your git repository URL
     - Example: `https://github.com/username/repo.git`
   - **Repository reference**: `refs/heads/master` (or your branch name)
   - **Compose path**: `docker-compose.yml`
   - **Authentication**: Add credentials if private repository
6. (Optional) Add environment variables:
   - `MCP_EXTERNAL_PORT`: Host port (default: 3000)
   - `LOG_LEVEL`: Logging level (default: INFO)
7. (Optional) Enable **Automatic updates** to rebuild on git changes
8. Click **Deploy the stack**

Portainer will clone your repository and build the image automatically!

**Troubleshooting:**
- If you get "uv.lock not found": Make sure the file is committed to git
- If build fails: Check Portainer logs for detailed error messages
- If authentication fails: Verify git credentials in Portainer settings

### Option B: Use Pre-built Image from Docker Hub

**Step 1: Build and Push Image**

```bash
# Build the image locally
docker build -t your-dockerhub-username/mcp-document-server:latest .

# Log in to Docker Hub
docker login

# Push the image
docker push your-dockerhub-username/mcp-document-server:latest
```

**Step 2: Deploy in Portainer**

1. Open Portainer web interface
2. Navigate to **Stacks** → **Add Stack**
3. Name your stack (e.g., `mcp-document-server`)
4. Choose **Web editor** method
5. Paste the contents of `docker-compose.portainer.yml`
6. Update the `image` field:
   ```yaml
   image: your-dockerhub-username/mcp-document-server:latest
   ```
7. Optionally add environment variables:
   - `MCP_EXTERNAL_PORT`: Host port (default: 3000)
   - `LOG_LEVEL`: Logging level (default: INFO)
8. Click **Deploy the stack**

### Option B: Use GitHub Container Registry (GHCR)

**Step 1: Build and Push to GHCR**

```bash
# Build the image
docker build -t ghcr.io/your-github-username/mcp-document-server:latest .

# Authenticate with GitHub
echo $GITHUB_TOKEN | docker login ghcr.io -u your-github-username --password-stdin

# Push to GHCR
docker push ghcr.io/your-github-username/mcp-document-server:latest
```

**Step 2: Deploy in Portainer**

Follow the same steps as Option A, but use:
```yaml
image: ghcr.io/your-github-username/mcp-document-server:latest
```

### Option C: Use Portainer's Build Agent (Advanced)

If you have a Portainer Business license, you can use the build agent:

1. Set up Portainer Edge Agent on the machine with source code
2. Use git repository deployment method
3. Portainer will clone and build on the agent

---

## Production Deployment

### Environment Variables

Create a `.env` file or set environment variables in Portainer:

```bash
# Server Configuration
MCP_SERVER_PORT=3000
MCP_EXTERNAL_PORT=3000
MCP_SERVER_HOST=0.0.0.0

# Logging
LOG_LEVEL=INFO
LOG_FILE=/logs/mcp_server.log

# OneDrive
DEFAULT_ONEDRIVE_PATH=/Documents/LibreChat
```

### Recommended Production Settings

**docker-compose.portainer.yml adjustments:**

```yaml
services:
  mcp-document-server:
    image: your-registry/mcp-document-server:v0.3.0  # Use version tags
    restart: always  # Change from unless-stopped

    # Remove development volume mount
    volumes:
      - ./logs:/logs
      # - ./src:/app/src  # REMOVE THIS LINE

    # Add resource limits
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 512M
```

### Persistent Logs

To persist logs across container restarts:

```bash
# Create logs directory
mkdir -p ./logs

# Ensure it's mounted in docker-compose
volumes:
  - ./logs:/logs
```

### Health Monitoring

The container includes a health check that runs every 30 seconds:

```bash
# Check health status
docker ps --filter name=mcp-document-server

# View health check logs
docker inspect mcp-document-server | jq '.[0].State.Health'
```

---

## Troubleshooting

### Issue: "uv.lock not found" in Portainer

**Cause:** Portainer cannot access local build context when building from Dockerfile.

**Solution:** Use a pre-built image as described in [Portainer Deployment](#portainer-deployment).

### Issue: Container keeps restarting

**Cause:** MCP server runs in STDIO mode and exits after initialization.

**Expected behavior:** This is correct for MCP servers. The server is designed to be controlled by LibreChat, which manages the lifecycle and communicates via stdin/stdout.

**For standalone testing:** The restarts are normal. The server initializes correctly each time.

### Issue: Port 3000 already in use

**Solution:** Use a custom port:

```bash
# In .env file
MCP_EXTERNAL_PORT=8080

# Or in Portainer environment variables
MCP_EXTERNAL_PORT=8080
```

### Issue: Cannot connect to server

**Check:**
1. Container is running: `docker ps`
2. Port mapping is correct: `docker port mcp-document-server`
3. Firewall allows connections to the port
4. Server is listening: `docker logs mcp-document-server`

### Issue: Image is too large

**Current size:** ~150-200MB (optimized with Python 3.11-slim)

**To reduce further:**
- Use multi-stage builds (already implemented)
- Remove unnecessary dependencies
- Use alpine base (requires additional C library setup)

### Viewing Logs

```bash
# Docker Compose
docker-compose logs -f

# Docker
docker logs -f mcp-document-server

# Portainer
Navigate to Container → Logs in the Portainer UI
```

---

## Updating the Deployment

### Update Image Version

```bash
# Build new version
docker build -t your-registry/mcp-document-server:v0.4.0 .

# Push to registry
docker push your-registry/mcp-document-server:v0.4.0

# Update in Portainer
# 1. Edit stack
# 2. Update image tag to v0.4.0
# 3. Click "Update the stack"
```

### Rolling Back

```bash
# If something goes wrong, revert to previous version
# Edit stack in Portainer
# Change image tag back to previous version
# Click "Update the stack"
```

---

## Integration with LibreChat

Once deployed, configure LibreChat to connect to the MCP server:

1. Ensure LibreChat can reach the server (same network or exposed port)
2. Configure `librechat.yaml` (see [README.md](README.md#librechat-configuration))
3. Set up Azure OAuth (see [AZURE_SETUP.md](AZURE_SETUP.md))

**Example LibreChat configuration:**

```yaml
mcpServers:
  document-generator:
    type: streamable-http
    url: "http://mcp-document-server:3000"  # Docker network name
    # OR
    url: "http://your-server-ip:3000"       # If on different host
    initTimeout: 150000
    oauth:
      provider: "microsoft"
      clientId: "${MICROSOFT_CLIENT_ID}"
      clientSecret: "${MICROSOFT_CLIENT_SECRET}"
      authorizationUrl: "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
      tokenUrl: "https://login.microsoftonline.com/common/oauth2/v2.0/token"
      scope: "Files.ReadWrite User.Read offline_access"
    headers:
      Authorization: "Bearer {{OAUTH_ACCESS_TOKEN}}"
      X-User-ID: "{{LIBRECHAT_USER_ID}}"
```

---

## Security Considerations

- **Token Storage:** This server is stateless. LibreChat manages all OAuth tokens.
- **Network Security:** Use Docker networks to isolate services.
- **Firewall:** Only expose port 3000 to LibreChat, not the internet.
- **Updates:** Regularly update the image for security patches.
- **Logs:** Monitor logs for suspicious activity.

---

## Support

For issues or questions:
- Check [TASK_TRACKER.md](TASK_TRACKER.md) for known issues
- Review [README.md](README.md) for general information
- See [AZURE_SETUP.md](AZURE_SETUP.md) for OAuth setup

---

**Last Updated:** 2025-10-13
**Version:** 0.3.0 (Phase 3 - Complete)
