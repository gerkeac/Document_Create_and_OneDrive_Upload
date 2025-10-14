# OAuth Discovery Verification - MCP Document Server

**Date:** 2025-10-14
**Status:** ✅ VERIFIED WORKING

## Summary

OAuth capability broadcasting **IS working correctly**! The MCP server successfully broadcasts OAuth authentication requirements via the MCP protocol using the OAuth Proxy pattern.

## Test Results

### 1. OAuth Discovery via 401 Response ✅

**Test:**
```bash
curl -i http://localhost:3010/mcp
```

**Result:**
```http
HTTP/1.1 401 Unauthorized
www-authenticate: Bearer error="invalid_token",
                  error_description="Authentication required",
                  resource_metadata="https://localhost:3010/.well-known/oauth-protected-resource"
```

**Verdict:** ✅ Server correctly returns 401 with WWW-Authenticate header pointing to OAuth metadata

### 2. OAuth Authorization Server Metadata ✅

**Test:**
```bash
curl http://localhost:3010/.well-known/oauth-authorization-server
```

**Result:**
```json
{
    "issuer": "https://localhost:3010/",
    "authorization_endpoint": "https://localhost:3010/authorize",
    "token_endpoint": "https://localhost:3010/token",
    "registration_endpoint": "https://localhost:3010/register",
    "scopes_supported": [
        "Files.ReadWrite",
        "User.Read",
        "offline_access"
    ],
    "response_types_supported": ["code"],
    "grant_types_supported": ["authorization_code", "refresh_token"],
    "token_endpoint_auth_methods_supported": ["client_secret_post"],
    "code_challenge_methods_supported": ["S256"]
}
```

**Verdict:** ✅ Complete OAuth configuration exposed for MCP client discovery

### 3. Server Initialization Logs ✅

```
INFO - Configuring OAuth authentication with Microsoft Azure AD
INFO -   Tenant ID: 8a178b1e-4027-438c-934a-7250406dd5d9
INFO -   Client ID: a4d279e8...
INFO -   Base URL: https://localhost:3010
INFO -   Redirect Path: /oauth/callback
INFO -   Scopes: Files.ReadWrite User.Read offline_access
INFO -   Config URL: https://login.microsoftonline.com/.../openid-configuration
INFO - ✓ OAuth authentication provider initialized successfully
INFO -   MCP clients will auto-discover OAuth requirements
INFO - Initializing FastMCP server with OAuth capability broadcasting
```

**Verdict:** ✅ OIDCProxy successfully configured with Azure AD

## How OAuth Discovery Works

### The OAuth Proxy Pattern

The MCP server implements the **OAuth Proxy pattern** where it acts as a middleman between MCP clients (LibreChat) and the OAuth provider (Microsoft Azure AD).

```
┌─────────────┐         ┌──────────────┐         ┌─────────────────┐
│  LibreChat  │ ←─────→ │  MCP Server  │ ←─────→ │  Microsoft      │
│  (Client)   │         │  (Proxy)     │         │  Azure AD       │
└─────────────┘         └──────────────┘         └─────────────────┘
```

**Why endpoints point to the MCP server:**
- Microsoft Azure AD doesn't support Dynamic Client Registration (DCR)
- MCP protocol expects DCR-compliant OAuth
- The proxy translates between MCP's DCR expectations and Azure's traditional OAuth
- This is **intentional and correct behavior**

### Complete OAuth Flow

#### Phase 1: Discovery

1. **LibreChat connects to MCP server** (unauthenticated)
   ```
   GET http://localhost:3010/mcp
   ```

2. **Server responds with 401 + WWW-Authenticate**
   ```http
   HTTP/1.1 401 Unauthorized
   WWW-Authenticate: Bearer resource_metadata="https://localhost:3010/.well-known/oauth-protected-resource"
   ```

3. **LibreChat discovers OAuth requirements**
   ```
   GET http://localhost:3010/.well-known/oauth-authorization-server
   ```

4. **LibreChat learns:**
   - Authorization endpoint: `https://localhost:3010/authorize`
   - Token endpoint: `https://localhost:3010/token`
   - Supported scopes: Files.ReadWrite, User.Read, offline_access
   - PKCE required (S256)

#### Phase 2: Authorization (Via Proxy)

1. **LibreChat redirects user to MCP server's authorize endpoint**
   ```
   https://localhost:3010/authorize?
     client_id=...&
     redirect_uri=...&
     scope=Files.ReadWrite+User.Read+offline_access&
     code_challenge=...&
     code_challenge_method=S256
   ```

2. **MCP Server (Proxy) redirects to Microsoft**
   ```
   Internally redirects to:
   https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?...
   ```

3. **User authenticates with Microsoft**
   - User logs in to Microsoft account
   - Grants permissions to the application
   - Microsoft redirects back to MCP server callback

4. **Microsoft redirects to MCP server**
   ```
   https://localhost:3010/oauth/callback?code=...&state=...
   ```

5. **MCP Server exchanges code for token**
   - Server uses its configured client_id and client_secret
   - Exchanges authorization code with Microsoft
   - Receives access token and refresh token

6. **MCP Server returns token to LibreChat**
   - LibreChat receives access token
   - LibreChat stores token (encrypted) in database

#### Phase 3: Authenticated Requests

1. **LibreChat makes tool call with token**
   ```
   POST http://localhost:3010/mcp
   Authorization: Bearer <access_token>
   ```

2. **MCP Server validates token**
   - FastMCP's OIDCProxy validates the token
   - Checks signature, expiration, audience, scopes
   - Extracts user info from validated token

3. **Tool function receives authenticated context**
   ```python
   ctx.meta['user'] = {
       'sub': 'user-id',
       'access_token': '<token>',
       'scopes': ['Files.ReadWrite', 'User.Read']
   }
   ```

4. **Server uses token for Microsoft Graph API**
   - Extracts token from authenticated context
   - Calls Microsoft Graph API to access OneDrive
   - Returns result to LibreChat

## Key Findings

### ✅ OAuth Discovery IS Broadcasting

The MCP server successfully broadcasts OAuth requirements through:
1. **401 Unauthorized responses** - MCP protocol standard
2. **WWW-Authenticate headers** - Points to OAuth metadata
3. **OAuth authorization server metadata** - Complete configuration
4. **MCP-compliant OAuth endpoints** - Authorization, token, registration

### ✅ Proxy Pattern IS Correct

The OAuth endpoints pointing to the MCP server (not directly to Microsoft) is **correct** because:
- This is the OAuth Proxy pattern recommended by FastMCP
- It bridges non-DCR providers (Microsoft) with DCR-expecting clients (LibreChat)
- It provides a transparent layer between client and provider
- It's the same pattern used by WorkOS, Auth0 integrations

### ✅ MCP Protocol Compliance

The implementation follows the MCP OAuth specification:
- ✅ Returns 401 for unauthenticated requests
- ✅ Includes WWW-Authenticate header with resource metadata
- ✅ Exposes OAuth authorization server metadata
- ✅ Supports authorization_code grant type
- ✅ Requires PKCE (S256)
- ✅ Declares required scopes

## Comparison: With vs Without OAuth Broadcasting

### Without OAuth Broadcasting (Passthrough Mode)

```yaml
# LibreChat config - Manual OAuth configuration required
mcpServers:
  document-generator:
    url: "http://localhost:3010"
    oauth:
      provider: "microsoft"
      clientId: "${MICROSOFT_CLIENT_ID}"
      clientSecret: "${MICROSOFT_CLIENT_SECRET}"
      authorizationUrl: "https://login.microsoftonline.com/.../authorize"
      tokenUrl: "https://login.microsoftonline.com/.../token"
      scope: "Files.ReadWrite User.Read offline_access"
    headers:
      Authorization: "Bearer {{OAUTH_ACCESS_TOKEN}}"
```

**Problems:**
- Manual configuration required (error-prone)
- OAuth endpoints hardcoded in LibreChat
- No automatic discovery
- Must update LibreChat config if OAuth settings change

### With OAuth Broadcasting (Current)

```yaml
# LibreChat config - Simplified!
mcpServers:
  document-generator:
    url: "http://localhost:3010"
    # OAuth settings auto-discovered from MCP server!
```

**Benefits:**
- ✅ Automatic OAuth discovery
- ✅ No manual endpoint configuration
- ✅ MCP server is single source of truth
- ✅ LibreChat adapts automatically to OAuth changes
- ✅ Standard MCP protocol compliance

## Environment Configuration

### Current Setup (OAuth Enabled)

```bash
# .env file
MICROSOFT_CLIENT_ID=your_microsoft_client_id_here
MICROSOFT_CLIENT_SECRET=your_microsoft_client_secret_here
MICROSOFT_TENANT_ID=your_microsoft_tenant_id_here
MCP_BASE_URL=https://localhost:3010
```

**Result:** OAuth capability broadcasting enabled ✅

### What Happens Without These Variables

```bash
# .env file (OAuth disabled)
# MICROSOFT_CLIENT_ID=
# MICROSOFT_CLIENT_SECRET=
```

**Result:** Server runs in passthrough mode, no OAuth broadcasting

## Testing OAuth Discovery

### Test 1: Check OAuth is Enabled

```bash
docker logs mcp-document-server | grep "OAuth"
```

**Expected Output:**
```
INFO - Configuring OAuth authentication with Microsoft Azure AD
INFO - ✓ OAuth authentication provider initialized successfully
INFO - Initializing FastMCP server with OAuth capability broadcasting
```

### Test 2: Check 401 Response

```bash
curl -i http://localhost:3010/mcp
```

**Expected:**
- Status: `401 Unauthorized`
- Header: `WWW-Authenticate: Bearer ...`

### Test 3: Check OAuth Metadata

```bash
curl http://localhost:3010/.well-known/oauth-authorization-server | jq .
```

**Expected:**
- `authorization_endpoint`: Present
- `token_endpoint`: Present
- `scopes_supported`: Files.ReadWrite, User.Read, offline_access
- `code_challenge_methods_supported`: ["S256"]

### Test 4: Check Server Logs for Requests

```bash
docker logs -f mcp-document-server
```

Then access the OAuth metadata endpoint and watch for log entries.

## Next Steps

### For Production Deployment

1. **Update MCP_BASE_URL** to use production URL:
   ```bash
   MCP_BASE_URL=https://your-cloudflare-tunnel.com
   ```

2. **Add redirect URI to Azure App Registration:**
   - Go to Azure Portal → App Registration → Authentication
   - Add: `https://your-cloudflare-tunnel.com/oauth/callback`

3. **Update LibreChat configuration:**
   ```yaml
   mcpServers:
     document-generator:
       url: "https://your-cloudflare-tunnel.com"
       # OAuth auto-discovered!
   ```

4. **Test OAuth flow end-to-end:**
   - LibreChat should discover OAuth requirements
   - User should be redirected to Microsoft login
   - After authentication, user should be redirected back to LibreChat
   - Tools requiring OneDrive should work automatically

### For Local Testing

1. **MCP_BASE_URL must be accessible from LibreChat:**
   - If LibreChat is in same Docker network: `http://mcp-document-server:3000`
   - If LibreChat is external: `http://localhost:3010`
   - For HTTPS testing: Use ngrok or cloudflare tunnel

2. **Azure redirect URI must match:**
   - Must include: `{MCP_BASE_URL}/oauth/callback`
   - Example: `http://localhost:3010/oauth/callback`

## Conclusion

✅ **OAuth discovery is working correctly and broadcasting successfully!**

The implementation:
- Follows MCP protocol OAuth specification
- Uses FastMCP's OIDCProxy for OAuth Proxy pattern
- Broadcasts OAuth requirements via 401 + WWW-Authenticate
- Exposes complete OAuth metadata for auto-discovery
- Acts as transparent proxy between LibreChat and Microsoft Azure AD

**Next action:** Test with LibreChat to verify end-to-end OAuth flow works as expected.

---

**Verified by:** Claude Code
**Date:** 2025-10-14
**MCP Server Version:** Document Generator v0.3.0
**FastMCP Version:** 2.12.4
