# OAuth Capability Broadcasting - MCP Document Server

## Overview

This MCP server supports **OAuth capability broadcasting** via the Model Context Protocol (MCP). When enabled, MCP clients like LibreChat can automatically discover authentication requirements and handle the OAuth flow without manual configuration.

## What is OAuth Capability Broadcasting?

OAuth capability broadcasting is a feature of the MCP protocol that allows servers to advertise their authentication requirements to clients. When a client connects to the server, the server declares:

- That OAuth authentication is required
- Which OAuth provider to use (Microsoft Azure AD in our case)
- What scopes/permissions are needed
- OAuth endpoints (authorization URL, token URL, etc.)

This enables **automatic discovery** - clients don't need to be manually configured with OAuth settings. They can discover everything they need directly from the server.

## Two Operating Modes

The MCP Document Server supports two authentication modes:

### Mode 1: OAuth Capability Broadcasting (Recommended)

**How it works:**
1. Server broadcasts OAuth requirements via MCP protocol
2. LibreChat auto-discovers the requirements
3. LibreChat performs OAuth flow with Microsoft
4. LibreChat passes validated tokens to the server
5. Server validates tokens using FastMCP's OIDCProxy

**Benefits:**
- ✅ Automatic discovery - no manual OAuth configuration in LibreChat
- ✅ Better security - server validates tokens
- ✅ Standardized MCP authentication flow
- ✅ Easier setup and maintenance

**Required Configuration:**
```bash
# In .env file
MICROSOFT_CLIENT_ID=your-azure-app-client-id
MICROSOFT_CLIENT_SECRET=your-azure-app-client-secret
MICROSOFT_TENANT_ID=common  # or your specific tenant ID
MCP_BASE_URL=https://your-server-public-url.com
```

### Mode 2: Passthrough Mode (Current - Legacy)

**How it works:**
1. Server does NOT broadcast OAuth requirements
2. LibreChat must be manually configured with OAuth settings
3. LibreChat performs OAuth flow with Microsoft
4. LibreChat passes tokens via `Authorization` header
5. Server extracts and uses tokens without validation

**Benefits:**
- ✅ Simpler server configuration (no OAuth credentials needed)
- ✅ Works with any OAuth provider LibreChat supports
- ✅ Server remains stateless

**Limitations:**
- ❌ Manual configuration required in LibreChat
- ❌ No server-side token validation
- ❌ Not using MCP's standardized auth flow

**Required Configuration:**
```bash
# In .env file
# Leave MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET empty
```

## Enabling OAuth Capability Broadcasting

### Step 1: Configure Azure App Registration

Follow [AZURE_SETUP.md](AZURE_SETUP.md) to create an Azure App Registration and obtain:
- Application (client) ID
- Client Secret
- Tenant ID

**Important:** Make sure to add the redirect URI for your MCP server:
- Format: `{MCP_BASE_URL}/oauth/callback`
- Example: `https://your-server.com/oauth/callback`

### Step 2: Configure Environment Variables

Edit your `.env` file:

```bash
# Enable OAuth capability broadcasting
MICROSOFT_CLIENT_ID=12345678-1234-1234-1234-123456789abc
MICROSOFT_CLIENT_SECRET=your-azure-client-secret-here
MICROSOFT_TENANT_ID=common  # or your specific tenant ID

# Public base URL of your MCP server (required!)
MCP_BASE_URL=https://your-server.com

# Optional: customize OAuth settings
MICROSOFT_OAUTH_SCOPES=Files.ReadWrite User.Read offline_access
MCP_AUTH_REDIRECT_PATH=/oauth/callback
```

**Critical:** `MCP_BASE_URL` must be the publicly accessible URL of your server:
- For Cloudflare Tunnel: `https://your-tunnel.trycloudflare.com`
- For direct access: `https://your-domain.com`
- For Docker Compose (if LibreChat is in same network): `http://mcp-document-server:3000`
- **NOT for local testing only:** `http://localhost:3010` (won't work from LibreChat unless it's on the same machine)

### Step 3: Restart the Server

```bash
docker-compose down
docker-compose up -d
```

Check the logs to confirm OAuth is enabled:

```bash
docker logs mcp-document-server
```

You should see:
```
INFO - Configuring OAuth authentication with Microsoft Azure AD
INFO - ✓ OAuth authentication provider initialized successfully
INFO - Initializing FastMCP server with OAuth capability broadcasting
```

### Step 4: Configure LibreChat (Simplified)

When OAuth capability broadcasting is enabled, LibreChat's configuration becomes much simpler:

**Before (Passthrough Mode):**
```yaml
mcpServers:
  document-generator:
    type: streamable-http
    url: "http://mcp-document-server:3000"
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

**After (OAuth Capability Broadcasting):**
```yaml
mcpServers:
  document-generator:
    type: streamable-http
    url: "http://mcp-document-server:3000"
    # OAuth settings will be auto-discovered from the MCP server!
```

LibreChat will:
1. Connect to the MCP server
2. Discover that OAuth is required
3. Discover the OAuth provider details
4. Perform the OAuth flow automatically
5. Pass validated tokens to the server

## How OAuth Discovery Works

When LibreChat connects to your MCP server with OAuth capability broadcasting enabled:

### 1. Initial Connection

LibreChat sends an `initialize` request to the MCP server.

### 2. OAuth Metadata Discovery

The server exposes OAuth metadata at standardized endpoints:
- `/.well-known/oauth-protected-resource` - Declares that OAuth is required
- OAuth provider endpoints from Azure AD's OIDC discovery

### 3. Client Registration

LibreChat uses the discovered metadata to:
- Identify the OAuth provider (Microsoft Azure AD)
- Get authorization and token URLs
- Learn required scopes
- Configure redirect URIs

### 4. Authorization Flow

LibreChat initiates the OAuth flow:
1. Redirects user to Microsoft login
2. User authenticates and grants permissions
3. Microsoft redirects back to LibreChat with authorization code
4. LibreChat exchanges code for access token
5. LibreChat stores the token (encrypted)

### 5. Authenticated Requests

For subsequent MCP tool calls:
1. LibreChat includes the access token in the request
2. FastMCP's OIDCProxy validates the token
3. Server extracts user info from validated token
4. Tool functions receive authenticated context

## Token Flow Comparison

### Passthrough Mode (Current)

```
┌─────────────┐                    ┌──────────────┐                    ┌─────────────┐
│             │  Manual OAuth      │              │  Bearer Token      │             │
│  LibreChat  │  Config in YAML    │   Microsoft  │  in Authorization  │ MCP Server  │
│             ├───────────────────>│   Azure AD   │  Header (no        │ (Passthrough│
│             │                    │              │  validation)       │  Mode)      │
│             │<───────────────────┤              ├───────────────────>│             │
└─────────────┘  Access Token      └──────────────┘                    └─────────────┘
                 (LibreChat stores)
```

### OAuth Capability Broadcasting (New)

```
┌─────────────┐                    ┌──────────────┐                    ┌─────────────┐
│             │  1. Auto-discover  │              │  2. OAuth Flow     │             │
│  LibreChat  │  OAuth requirements│   Microsoft  │                    │ MCP Server  │
│             │<───────────────────┤   Azure AD   │                    │ (Auth       │
│             │                    │              │                    │  Enabled)   │
│             │  3. Get Access     │              │  4. Validated      │             │
│             │     Token          │              │     Token in       │             │
│             ├───────────────────>│              │     Context        │             │
│             │                    └──────────────┘                    │             │
│             │                                      ┌─────────────────┤             │
│             ├─────────────────────────────────────>│ OIDCProxy       │             │
└─────────────┘  5. Tool call with token            │ validates token │             │
                                                     └─────────────────┴─────────────┘
```

## Security Benefits

OAuth capability broadcasting provides several security advantages:

### 1. Server-Side Token Validation

**Passthrough Mode:**
- Server trusts any token passed in headers
- No validation of token authenticity
- Vulnerable to token forgery

**OAuth Broadcasting:**
- Server validates token signature
- Verifies token issuer (Microsoft)
- Checks token expiration
- Validates audience and scopes

### 2. Centralized OAuth Configuration

**Passthrough Mode:**
- OAuth credentials duplicated in LibreChat config
- Risk of misconfiguration
- Harder to audit

**OAuth Broadcasting:**
- OAuth credentials only in server config
- Single source of truth
- Easier to rotate secrets

### 3. Protocol-Level Authentication

**Passthrough Mode:**
- Application-level auth (custom headers)
- Not standardized
- Harder for clients to implement

**OAuth Broadcasting:**
- MCP protocol-level auth
- Standardized approach
- Better interoperability

## Troubleshooting

### Issue: Server starts in passthrough mode despite OAuth config

**Symptoms:**
```
INFO - OAuth authentication disabled - MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET not configured
INFO - Initializing FastMCP server in passthrough mode
```

**Solutions:**
1. Check `.env` file has OAuth credentials uncommented
2. Verify environment variables are being passed to Docker:
   ```bash
   docker exec mcp-document-server env | grep MICROSOFT
   ```
3. Ensure no typos in variable names
4. Restart container after changing `.env`:
   ```bash
   docker-compose down && docker-compose up -d
   ```

### Issue: MCP_BASE_URL not configured

**Symptoms:**
```
WARNING - MCP_BASE_URL not configured - OAuth authentication cannot be enabled
```

**Solution:**
Set `MCP_BASE_URL` in `.env` to your server's public URL:
```bash
MCP_BASE_URL=https://your-cloudflare-tunnel.com
```

### Issue: LibreChat can't discover OAuth requirements

**Symptoms:**
- LibreChat shows "Connection failed" or "Authentication required"
- No OAuth prompt appears

**Solutions:**
1. Verify server logs show OAuth is enabled:
   ```bash
   docker logs mcp-document-server | grep "OAuth"
   ```
2. Check MCP_BASE_URL is accessible from LibreChat
3. Test OAuth metadata endpoint:
   ```bash
   curl http://your-server:3000/.well-known/oauth-protected-resource
   ```
4. Ensure LibreChat version supports OAuth discovery (check LibreChat docs)

### Issue: OAuth flow fails with redirect_uri mismatch

**Symptoms:**
```
error: redirect_uri_mismatch
```

**Solutions:**
1. Add redirect URI to Azure App Registration:
   - Format: `{MCP_BASE_URL}/oauth/callback`
   - Example: `https://your-server.com/oauth/callback`
2. Ensure `MCP_BASE_URL` in `.env` matches public URL exactly
3. Check for trailing slashes (should not have them)
4. Verify HTTPS vs HTTP matches

## Testing OAuth Capability Broadcasting

### 1. Test Server Startup

```bash
docker logs mcp-document-server | grep -A 10 "OAuth"
```

Expected output:
```
INFO - Configuring OAuth authentication with Microsoft Azure AD
INFO -   Tenant ID: common
INFO -   Client ID: 12345678...
INFO -   Base URL: https://your-server.com
INFO -   Redirect Path: /oauth/callback
INFO -   Scopes: Files.ReadWrite User.Read offline_access
INFO - ✓ OAuth authentication provider initialized successfully
INFO -   MCP clients will auto-discover OAuth requirements
```

### 2. Test MCP Initialize Response

```bash
curl -X POST http://localhost:3010/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

With OAuth enabled, the response should include authentication capabilities in the server metadata.

### 3. Test with LibreChat

1. Configure LibreChat with minimal MCP server config (just URL)
2. Start LibreChat
3. Connect to the MCP server
4. Look for OAuth authentication prompt
5. Complete OAuth flow
6. Try using a tool that requires OneDrive access
7. Check server logs for token validation

## Migration Guide

### Migrating from Passthrough Mode to OAuth Broadcasting

**Step 1:** Take note of your current Azure App Registration details
- Client ID
- Client Secret
- Tenant ID

**Step 2:** Update your `.env` file with the OAuth configuration:
```bash
MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
MICROSOFT_TENANT_ID=common
MCP_BASE_URL=https://your-public-url.com
```

**Step 3:** Add redirect URI to Azure App Registration:
- Go to Azure Portal → App Registration → Authentication
- Add redirect URI: `https://your-public-url.com/oauth/callback`
- Save changes

**Step 4:** Simplify LibreChat configuration (remove manual OAuth config):
```yaml
# Before
mcpServers:
  document-generator:
    type: streamable-http
    url: "http://mcp-document-server:3000"
    oauth:
      provider: "microsoft"
      # ... lots of manual config
    headers:
      Authorization: "Bearer {{OAUTH_ACCESS_TOKEN}}"
      X-User-ID: "{{LIBRECHAT_USER_ID}}"

# After
mcpServers:
  document-generator:
    type: streamable-http
    url: "http://mcp-document-server:3000"
    # OAuth will be auto-discovered!
```

**Step 5:** Restart services:
```bash
# Restart MCP server
docker-compose restart mcp-document-server

# Restart LibreChat (in LibreChat directory)
docker-compose restart librechat
```

**Step 6:** Test the OAuth flow:
1. Open LibreChat
2. Create a new chat
3. Look for OAuth authentication prompt for the MCP server
4. Complete authentication
5. Try creating a document with OneDrive upload

## References

- [FastMCP Authentication Documentation](https://gofastmcp.com/servers/auth/authentication)
- [FastMCP OIDC Proxy Documentation](https://gofastmcp.com/servers/auth/oidc-proxy)
- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)
- [Microsoft Identity Platform OAuth 2.0](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow)
- [Azure App Registration Setup Guide](AZURE_SETUP.md)
- [LibreChat MCP Documentation](LIBRECHAT_MCP.md)

---

**Last Updated:** 2025-10-14
**Version:** 1.0
**Status:** Ready for Testing
