# Microsoft Azure App Registration Setup Guide

This guide walks you through setting up a Microsoft Azure App Registration for OneDrive integration with the MCP Document Generator Server.

## Prerequisites

- A Microsoft Azure account (free tier is sufficient)
- Access to [Azure Portal](https://portal.azure.com)
- LibreChat instance with MCP support

## Step 1: Create App Registration

1. **Navigate to Azure Portal**
   - Go to [Azure Portal](https://portal.azure.com)
   - Sign in with your Microsoft account

2. **Open App Registrations**
   - In the search bar at the top, type "App registrations"
   - Click on "App registrations" under Services

3. **Create New Registration**
   - Click "+ New registration" button
   - Fill in the details:
     - **Name**: `LibreChat MCP Document Generator` (or your preferred name)
     - **Supported account types**: Select one of:
       - **Multitenant** (recommended): "Accounts in any organizational directory (Any Azure AD directory - Multitenant) and personal Microsoft accounts"
       - **Single tenant**: If you only want to support your organization
     - **Redirect URI**: Leave blank for now (we'll configure this for LibreChat OAuth later)
   - Click "Register"

4. **Note Your Application Details**
   - After registration, you'll see the Overview page
   - **Copy and save these values** (you'll need them later):
     - **Application (client) ID**: e.g., `12345678-1234-1234-1234-123456789abc`
     - **Directory (tenant) ID**: e.g., `87654321-4321-4321-4321-cba987654321`

## Step 2: Configure API Permissions

1. **Navigate to API Permissions**
   - In the left sidebar, click "API permissions"
   - You'll see "Microsoft Graph" with "User.Read" already added

2. **Add Required Permissions**
   - Click "+ Add a permission"
   - Select "Microsoft Graph"
   - Select "Delegated permissions"
   - Search for and add:
     - `Files.ReadWrite` - Read and write access to user files
     - `Files.ReadWrite.All` - (Optional) For broader access if needed
     - `User.Read` - (Already included) Basic user profile information
     - `offline_access` - (Recommended) Enable refresh tokens for long-lived sessions
   - Click "Add permissions"

3. **Grant Admin Consent (Optional)**
   - If you're an admin and want to pre-approve for all users in your organization:
     - Click "Grant admin consent for [Your Organization]"
     - Click "Yes" to confirm

## Step 3: Create Client Secret

1. **Navigate to Certificates & secrets**
   - In the left sidebar, click "Certificates & secrets"
   - Click on the "Client secrets" tab

2. **Create New Client Secret**
   - Click "+ New client secret"
   - Fill in the details:
     - **Description**: `LibreChat MCP Server Secret` (or your preferred name)
     - **Expires**: Select expiration period
       - **Recommended**: 24 months (longest option)
       - **Note**: You'll need to create a new secret before expiration
   - Click "Add"

3. **Copy Client Secret Value**
   - **IMPORTANT**: Copy the secret **Value** immediately
   - **You cannot view this secret again** after leaving this page
   - Store it securely (you'll add it to your `.env` file)

## Step 4: Configure OAuth Client Discovery (For LibreChat)

LibreChat supports automatic OAuth client registration through Client Discovery. For this to work, your MCP server needs to expose OAuth metadata.

**Current Implementation Status**: Phase 2 will implement this. For now, we'll use the standard OAuth flow where LibreChat handles the OAuth redirect.

### Redirect URI Configuration

1. **Get LibreChat OAuth Callback URL**
   - Your LibreChat OAuth callback URL will be:
     - Local: `http://localhost:3000/oauth/callback`
     - Production: `https://your-librechat-domain.com/oauth/callback`

2. **Add Redirect URI to Azure**
   - Go back to your App Registration in Azure Portal
   - Click "Authentication" in the left sidebar
   - Click "+ Add a platform"
   - Select "Web"
   - Enter your callback URL(s):
     - `http://localhost:3000/oauth/callback` (for local development)
     - `https://your-librechat-domain.com/oauth/callback` (for production)
   - Under "Implicit grant and hybrid flows", ensure:
     - ✅ "Access tokens" is checked
     - ✅ "ID tokens" is checked
   - Click "Configure"

## Step 5: Configure Environment Variables

1. **Copy Environment Template**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file**
   ```bash
   nano .env
   ```

3. **Add Your Azure Credentials**
   ```env
   # Microsoft OAuth Configuration
   MICROSOFT_CLIENT_ID=your-application-client-id-here
   MICROSOFT_CLIENT_SECRET=your-client-secret-value-here
   MICROSOFT_TENANT_ID=common  # Use 'common' for multitenant, or your tenant ID
   MICROSOFT_REDIRECT_URI=http://localhost:3000/oauth/callback

   # Token Storage Configuration
   TOKEN_ENCRYPTION_KEY=your-generated-encryption-key-here
   TOKEN_STORAGE_PATH=/data/tokens
   ```

4. **Generate Token Encryption Key**
   ```bash
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
   - Copy the output and paste it as `TOKEN_ENCRYPTION_KEY` in your `.env` file

## Step 6: Configure LibreChat

Add the MCP server configuration to your `librechat.yaml`:

```yaml
mcpServers:
  document-generator:
    type: streamable-http
    url: "http://mcp-document-server:3000"  # Adjust for your deployment
    initTimeout: 150000  # 150 seconds to allow for OAuth flow
    oauth:
      provider: "microsoft"
      clientId: "${MICROSOFT_CLIENT_ID}"
      clientSecret: "${MICROSOFT_CLIENT_SECRET}"
      authorizationUrl: "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
      tokenUrl: "https://login.microsoftonline.com/common/oauth2/v2.0/token"
      scope: "Files.ReadWrite User.Read offline_access"
    headers:
      Authorization: "Bearer {{OAUTH_ACCESS_TOKEN}}"  # LibreChat passes the OAuth token
      X-User-ID: "{{LIBRECHAT_USER_ID}}"  # User identification
    serverInstructions: true
```

**Note**: Replace `http://mcp-document-server:3000` with your actual MCP server URL:
- Local development: `http://localhost:3000`
- Docker Compose: `http://mcp-document-server:3000`
- Production: Your Cloudflare tunnel URL or direct server URL

## Step 7: Test OAuth Flow

1. **Start Your MCP Server**
   ```bash
   docker-compose up --build
   ```

2. **Start LibreChat**
   ```bash
   # In your LibreChat directory
   docker-compose up
   ```

3. **Test Authentication**
   - Open LibreChat in your browser
   - Create a new chat or select an existing one
   - Look for the MCP Settings panel or server status indicator
   - You should see "OAuth Required" status for `document-generator`
   - Click the authentication button
   - You'll be redirected to Microsoft login
   - After successful authentication, you'll be redirected back to LibreChat
   - The server status should change to "Connected"

4. **Test Document Generation**
   - In LibreChat chat, ask the AI:
     - "Create a Word document with a title 'Test Document' and upload it to my OneDrive"
   - The AI should use the `create_word_document` tool
   - Check your OneDrive for the generated document

## Troubleshooting

### Common Issues

**Issue: "Redirect URI mismatch" error**
- **Solution**: Ensure the redirect URI in Azure matches exactly what LibreChat is using
- Check both Azure Portal → Authentication → Redirect URIs
- Check `librechat.yaml` OAuth configuration

**Issue: "Invalid client secret" error**
- **Solution**: Verify you copied the secret **Value** (not the Secret ID)
- If lost, create a new client secret in Azure Portal

**Issue: "Insufficient permissions" error**
- **Solution**: Ensure you added `Files.ReadWrite` and `User.Read` permissions
- Grant admin consent if required by your organization

**Issue: OAuth token not being passed to MCP server**
- **Solution**: Check LibreChat logs for OAuth flow completion
- Verify `headers` configuration in `librechat.yaml` includes `Authorization: "Bearer {{OAUTH_ACCESS_TOKEN}}"`
- Check MCP server logs to see if `Authorization` header is received

**Issue: Token expires too quickly**
- **Solution**: Ensure `offline_access` scope is included in LibreChat OAuth configuration
- This enables refresh tokens for long-lived sessions
- LibreChat will automatically refresh tokens when they expire

### Logs to Check

**MCP Server Logs**:
```bash
docker-compose logs -f mcp-document-server
```

**LibreChat Logs**:
```bash
# In LibreChat directory
docker-compose logs -f librechat
```

Look for:
- `[MCP][document-generator] OAuth authentication required`
- `[MCP][document-generator] Successfully authenticated`
- `[MCP][document-generator] Token refreshed`

## Security Best Practices

1. **Never commit secrets to version control**
   - Ensure `.env` is in your `.gitignore`
   - Use environment variables for all sensitive data

2. **Rotate client secrets regularly**
   - Azure allows multiple active secrets
   - Create a new secret before the old one expires
   - Update `.env` and restart services

3. **Use HTTPS in production**
   - Never use `http://` for OAuth redirect URIs in production
   - Configure Cloudflare tunnel or proper HTTPS certificate

4. **Limit API permissions**
   - Only request permissions you actually need
   - Use `Files.ReadWrite` (not `Files.ReadWrite.All`) unless you need access to all files

5. **Monitor token usage**
   - Check MCP server logs for authentication failures
   - Set up alerts for repeated authentication errors

## Next Steps

After completing Azure setup:

1. Test basic OneDrive upload functionality
2. Verify multi-user isolation (each user authenticates separately)
3. Test token refresh flow (wait for token to expire or manually revoke)
4. Move to Phase 3 (PowerPoint and Excel generation)

## References

- [Microsoft Graph API Documentation](https://learn.microsoft.com/en-us/graph/)
- [Microsoft Identity Platform OAuth 2.0](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow)
- [LibreChat MCP Documentation](https://www.librechat.ai/docs/features/mcp)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)

---

**Last Updated**: 2025-10-13
**Phase**: Phase 2 - OneDrive Integration
