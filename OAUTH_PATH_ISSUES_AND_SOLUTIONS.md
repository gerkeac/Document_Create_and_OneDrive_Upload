# OAuth Path Issues and Solutions

**Date:** 2025-10-14
**Issue:** LibreChat OAuth discovery returning 404 errors for some endpoints

## The Problem

When LibreChat attempted to discover OAuth configuration from the MCP server, it received several 404 errors:

```
INFO: 172.30.0.1:52876 - "POST /mcp/register HTTP/1.1" 404 Not Found
INFO: 172.30.0.1:52876 - "GET /.well-known/oauth-protected-resource/mcp HTTP/1.1" 404 Not Found
INFO: 172.30.0.1:52876 - "GET /.well-known/oauth-protected-resource HTTP/1.1" 404 Not Found  ← Initially 404
INFO: 172.30.0.1:52876 - "GET /.well-known/oauth-authorization-server HTTP/1.1" 200 OK  ← Working
INFO: 172.30.0.1:52876 - "GET /.well-known/oauth-authorization-server/mcp HTTP/1.1" 404 Not Found
```

## Root Cause Analysis

### Issue #1: Missing oauth-protected-resource Endpoint ❌ → ✅ Fixed

**Problem:**
FastMCP's OIDCProxy doesn't provide the `/.well-known/oauth-protected-resource` endpoint required by RFC 9728 and the MCP protocol specification.

**Evidence:**
```bash
curl http://localhost:3010/.well-known/oauth-protected-resource
# Returns: Not Found
```

**Why It's Needed:**
According to MCP spec and RFC 9728, the OAuth Protected Resource Metadata endpoint must provide:
- List of authorization servers
- Supported scopes
- Bearer token methods

The `WWW-Authenticate` header references this endpoint:
```http
WWW-Authenticate: Bearer error="invalid_token",
                  resource_metadata="https://localhost:3010/.well-known/oauth-protected-resource"
```

**Solution:**
Added custom route to FastMCP server to provide this endpoint:

```python
@mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
def oauth_protected_resource_metadata(request: Any) -> JSONResponse:
    base_url = os.environ.get("MCP_BASE_URL", "http://localhost:3000")

    metadata = {
        "resource": base_url,
        "authorization_servers": [base_url],
        "scopes_supported": [
            "Files.ReadWrite",
            "User.Read",
            "offline_access"
        ],
        "bearer_methods_supported": ["header"],
        "resource_documentation": f"{base_url}/docs"
    }

    return JSONResponse(metadata)
```

**Result:** ✅ Endpoint now returns proper RFC 9728 metadata

### Issue #2: Path Confusion - /mcp vs Root Level

**Problem:**
LibreChat is attempting to access OAuth endpoints with `/mcp` suffix:
- `/mcp/register` (404) instead of `/register` (200)
- `/.well-known/oauth-authorization-server/mcp` (404) instead of `/.well-known/oauth-authorization-server` (200)
- `/.well-known/oauth-protected-resource/mcp` (404) instead of `/.well-known/oauth-protected-resource` (200)

**Why This Happens:**
The MCP protocol endpoint is mounted at `/mcp`:
```
http://localhost:3010/mcp  ← MCP protocol endpoint
```

LibreChat may be inferring that all server endpoints are under `/mcp` path, but OAuth endpoints are at root level:
```
http://localhost:3010/register  ← OAuth registration
http://localhost:3010/.well-known/*  ← OAuth metadata
http://localhost:3010/authorize  ← OAuth authorization
http://localhost:3010/token  ← OAuth token exchange
```

**Architecture:**
```
Server Root (/)
├── /mcp                              ← MCP protocol (tools, resources, prompts)
├── /register                         ← OAuth client registration
├── /authorize                        ← OAuth authorization
├── /token                            ← OAuth token exchange
├── /auth/callback                    ← OAuth callback
└── /.well-known/
    ├── oauth-authorization-server    ← OAuth server metadata
    └── oauth-protected-resource      ← OAuth resource metadata (our addition)
```

**This is Correct Behavior:**
- MCP protocol is at `/mcp`
- OAuth endpoints are at root level
- This separation is intentional and follows OAuth/OIDC standards

**Why LibreChat Tries `/mcp/*`:**
Possible reasons:
1. LibreChat assumes all endpoints are under the MCP base path
2. OAuth metadata discovery logic constructs incorrect URLs
3. LibreChat is trying both locations (with and without `/mcp`)

**Solution:**
The OAuth endpoints are correctly placed at root level. LibreChat should:
1. Discover OAuth endpoints from `/.well-known/oauth-authorization-server` metadata
2. Use the exact URLs provided in the metadata (no `/mcp` prefix)

The metadata explicitly provides correct paths:
```json
{
    "authorization_endpoint": "https://localhost:3010/authorize",
    "token_endpoint": "https://localhost:3010/token",
    "registration_endpoint": "https://localhost:3010/register"
}
```

**Status:** ⚠️ LibreChat should follow metadata URLs exactly. If it continues trying `/mcp/*` paths, it's a LibreChat bug/misconfiguration.

## Current Status Summary

### ✅ Working Endpoints

| Endpoint | Status | Response |
|----------|--------|----------|
| `/.well-known/oauth-authorization-server` | ✅ Working | Returns complete OAuth metadata |
| `/.well-known/oauth-protected-resource` | ✅ Fixed | Returns RFC 9728 metadata |
| `/register` | ✅ Working | OAuth client registration |
| `/authorize` | ✅ Working | OAuth authorization |
| `/token` | ✅ Working | OAuth token exchange |
| `/mcp` (unauthenticated) | ✅ Working | Returns 401 with WWW-Authenticate header |

### ❌ Expected 404s (Not Our Problem)

| Endpoint | Status | Why 404 is Correct |
|----------|--------|-------------------|
| `/mcp/register` | ❌ 404 | OAuth registration is at `/register`, not `/mcp/register` |
| `/.well-known/oauth-authorization-server/mcp` | ❌ 404 | Metadata is at root level, not under `/mcp` |
| `/.well-known/oauth-protected-resource/mcp` | ❌ 404 | Metadata is at root level, not under `/mcp` |

**These 404s are expected and correct.** LibreChat should not be appending `/mcp` to OAuth endpoint paths.

## Test Results

### Test 1: OAuth Authorization Server Metadata ✅
```bash
curl http://localhost:3010/.well-known/oauth-authorization-server | jq .
```
```json
{
    "issuer": "https://localhost:3010/",
    "authorization_endpoint": "https://localhost:3010/authorize",
    "token_endpoint": "https://localhost:3010/token",
    "registration_endpoint": "https://localhost:3010/register",
    "scopes_supported": ["Files.ReadWrite", "User.Read", "offline_access"],
    "response_types_supported": ["code"],
    "grant_types_supported": ["authorization_code", "refresh_token"],
    "token_endpoint_auth_methods_supported": ["client_secret_post"],
    "code_challenge_methods_supported": ["S256"]
}
```

**Verdict:** ✅ Complete OAuth configuration exposed correctly

### Test 2: OAuth Protected Resource Metadata ✅
```bash
curl http://localhost:3010/.well-known/oauth-protected-resource | jq .
```
```json
{
    "resource": "https://localhost:3010",
    "authorization_servers": ["https://localhost:3010"],
    "scopes_supported": ["Files.ReadWrite", "User.Read", "offline_access"],
    "bearer_methods_supported": ["header"],
    "resource_documentation": "https://localhost:3010/docs"
}
```

**Verdict:** ✅ RFC 9728 metadata now provided

### Test 3: MCP Endpoint 401 Response ✅
```bash
curl -i http://localhost:3010/mcp
```
```http
HTTP/1.1 401 Unauthorized
www-authenticate: Bearer error="invalid_token",
                  error_description="Authentication required",
                  resource_metadata="https://localhost:3010/.well-known/oauth-protected-resource"
```

**Verdict:** ✅ Correct 401 with WWW-Authenticate header pointing to metadata

### Test 4: Client Registration ✅
```bash
curl -X POST http://localhost:3010/register \
  -H "Content-Type: application/json" \
  -d '{"redirect_uris":["http://librechat:3000/oauth/callback"],"client_name":"LibreChat"}'
```
```json
{
    "redirect_uris": ["http://librechat:3000/oauth/callback"],
    "token_endpoint_auth_method": "client_secret_post",
    "grant_types": ["authorization_code", "refresh_token"],
    "response_types": ["code"],
    "client_name": "LibreChat",
    "client_id": "5f78df51-e8f9-4d61-8467-e6f1dde0305a",
    "client_secret": "4e93375a1b86ab5a91f0bbfd3253c4346ce9da7cfa4358aea026a8c063e9e204",
    "client_id_issued_at": 1760477949
}
```

**Verdict:** ✅ Dynamic client registration working

## OAuth Discovery Flow (Corrected)

### Phase 1: Discovery
1. **LibreChat → MCP Server (unauthenticated)**
   ```
   GET http://localhost:3010/mcp
   ```

2. **Server → 401 Unauthorized**
   ```http
   HTTP/1.1 401 Unauthorized
   WWW-Authenticate: Bearer resource_metadata="https://localhost:3010/.well-known/oauth-protected-resource"
   ```

3. **LibreChat → Fetch Protected Resource Metadata**
   ```
   GET https://localhost:3010/.well-known/oauth-protected-resource
   ```
   ```json
   {
       "authorization_servers": ["https://localhost:3010"]
   }
   ```

4. **LibreChat → Fetch Authorization Server Metadata**
   ```
   GET https://localhost:3010/.well-known/oauth-authorization-server
   ```
   ```json
   {
       "authorization_endpoint": "https://localhost:3010/authorize",
       "token_endpoint": "https://localhost:3010/token",
       "registration_endpoint": "https://localhost:3010/register",
       "scopes_supported": ["Files.ReadWrite", "User.Read", "offline_access"]
   }
   ```

### Phase 2: Registration (Optional)
5. **LibreChat → Register Client (DCR)**
   ```
   POST https://localhost:3010/register
   Body: {
       "redirect_uris": ["http://librechat:3000/oauth/callback"],
       "client_name": "LibreChat"
   }
   ```

6. **Server → Client Credentials**
   ```json
   {
       "client_id": "...",
       "client_secret": "..."
   }
   ```

### Phase 3: Authorization
7. **LibreChat → Redirect User to Authorization**
   ```
   GET https://localhost:3010/authorize?
       client_id=...&
       redirect_uri=http://librechat:3000/oauth/callback&
       scope=Files.ReadWrite+User.Read+offline_access&
       code_challenge=...&
       code_challenge_method=S256
   ```

8. **Proxy → Redirect to Microsoft**
   ```
   GET https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?...
   ```

9. **User authenticates, Microsoft → Callback to Proxy**
   ```
   GET https://localhost:3010/auth/callback?code=...&state=...
   ```

10. **Proxy → Exchange code with Microsoft, Return to LibreChat**
    ```
    302 Redirect → http://librechat:3000/oauth/callback?code=...
    ```

### Phase 4: Token Exchange
11. **LibreChat → Exchange Code for Token**
    ```
    POST https://localhost:3010/token
    Body: {
        "grant_type": "authorization_code",
        "code": "...",
        "redirect_uri": "http://librechat:3000/oauth/callback",
        "client_id": "...",
        "client_secret": "...",
        "code_verifier": "..."
    }
    ```

12. **Server → Access Token**
    ```json
    {
        "access_token": "...",
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "...",
        "scope": "Files.ReadWrite User.Read offline_access"
    }
    ```

### Phase 5: Authenticated Requests
13. **LibreChat → MCP Server (authenticated)**
    ```
    POST http://localhost:3010/mcp
    Authorization: Bearer <access_token>
    Body: MCP tool call
    ```

14. **Server validates token, executes tool, returns result**

## What We Fixed

1. ✅ Added missing `/.well-known/oauth-protected-resource` endpoint
2. ✅ Endpoint returns RFC 9728 compliant metadata
3. ✅ Proper WWW-Authenticate header pointing to correct metadata URL
4. ✅ OAuth endpoints remain at root level (correct behavior)

## What LibreChat Should Do

LibreChat should:
1. ✅ Parse `WWW-Authenticate` header from 401 response
2. ✅ Fetch metadata from `resource_metadata` URL (now works!)
3. ✅ Discover `authorization_servers` from protected resource metadata
4. ✅ Fetch OAuth configuration from `/.well-known/oauth-authorization-server`
5. ✅ Use exact URLs from metadata (don't append `/mcp`)

If LibreChat continues trying `/mcp/register` or other `/mcp/*` OAuth paths, it's likely:
- A bug in LibreChat's OAuth discovery logic
- Incorrect URL construction in LibreChat
- Not following metadata URLs exactly

## Recommendation

**For LibreChat Configuration:**

Make sure LibreChat MCP server URL points to the root, not `/mcp`:
```yaml
# Correct
mcpServers:
  document-generator:
    url: "http://localhost:3010"  # Root URL, not /mcp
```

The `/mcp` path is automatically discovered by the MCP protocol, not in the base URL.

**For Testing:**

All OAuth endpoints are now accessible:
- ✅ `/.well-known/oauth-authorization-server`
- ✅ `/.well-known/oauth-protected-resource` (newly added)
- ✅ `/register`
- ✅ `/authorize`
- ✅ `/token`
- ✅ `/auth/callback`

OAuth discovery should work correctly with these fixes.

## Files Modified

1. **[src/mcp_document_server/server.py](src/mcp_document_server/server.py)**
   - Added import: `from starlette.responses import JSONResponse`
   - Added custom route for `/.well-known/oauth-protected-resource`
   - Returns RFC 9728 compliant metadata

## Next Steps

1. Test with LibreChat to verify OAuth flow works end-to-end
2. Monitor logs for any remaining 404s
3. If LibreChat still tries `/mcp/*` OAuth paths, investigate LibreChat configuration/code

---

**Status:** ✅ All required OAuth endpoints now available
**Tested:** 2025-10-14
**Ready for:** LibreChat integration testing
