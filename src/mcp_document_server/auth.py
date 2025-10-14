"""OAuth authentication provider for Microsoft Azure AD integration.

This module provides FastMCP authentication capability broadcasting for
OneDrive integration. It uses the OIDCProxy pattern to enable automatic
OAuth discovery and token handling by MCP clients like LibreChat.
"""

import logging
import os

from fastmcp.server.auth.oidc_proxy import OIDCProxy

logger = logging.getLogger(__name__)


def create_auth_provider(base_url: str | None = None) -> OIDCProxy | None:
    """
    Create and configure the OAuth authentication provider for Microsoft Azure AD.

    This enables the MCP server to broadcast OAuth authentication requirements
    to clients, allowing automatic discovery and token management.

    Args:
        base_url: The public base URL of this MCP server (e.g., "https://your-server.com")
                  If not provided, will attempt to read from MCP_BASE_URL environment variable.

    Returns:
        Configured OIDCProxy instance if OAuth is enabled, None otherwise

    Environment Variables:
        MICROSOFT_CLIENT_ID: Azure App Registration client ID (required for auth)
        MICROSOFT_CLIENT_SECRET: Azure App Registration client secret (required for auth)
        MICROSOFT_TENANT_ID: Azure tenant ID (default: "common" for multitenant)
        MCP_BASE_URL: Public base URL of this server (required for OAuth)
        MCP_AUTH_REDIRECT_PATH: OAuth callback path (default: "/oauth/callback")
        MICROSOFT_OAUTH_SCOPES: Space-separated OAuth scopes (default: "Files.ReadWrite User.Read offline_access")
    """
    # Check if OAuth is configured
    client_id = os.environ.get("MICROSOFT_CLIENT_ID")
    client_secret = os.environ.get("MICROSOFT_CLIENT_SECRET")

    if not client_id or not client_secret:
        logger.info(
            "OAuth authentication disabled - MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET not configured"
        )
        logger.info(
            "Server will operate in passthrough mode, expecting clients to provide Bearer tokens via Authorization header"
        )
        return None

    # Get base URL
    if not base_url:
        base_url = os.environ.get("MCP_BASE_URL")

    if not base_url:
        logger.warning(
            "MCP_BASE_URL not configured - OAuth authentication cannot be enabled. "
            "Set MCP_BASE_URL to your server's public URL (e.g., https://your-server.com)"
        )
        return None

    # Configure Microsoft Azure AD OAuth
    tenant_id = os.environ.get("MICROSOFT_TENANT_ID", "common")
    config_url = (
        f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"
    )

    # OAuth scopes for OneDrive access
    scopes = os.environ.get("MICROSOFT_OAUTH_SCOPES", "Files.ReadWrite User.Read offline_access")

    # OAuth callback path
    redirect_path = os.environ.get("MCP_AUTH_REDIRECT_PATH", "/oauth/callback")

    logger.info("Configuring OAuth authentication with Microsoft Azure AD")
    logger.info(f"  Tenant ID: {tenant_id}")
    logger.info(f"  Client ID: {client_id[:8]}...")
    logger.info(f"  Base URL: {base_url}")
    logger.info(f"  Redirect Path: {redirect_path}")
    logger.info(f"  Scopes: {scopes}")
    logger.info(f"  Config URL: {config_url}")

    try:
        auth_provider = OIDCProxy(
            config_url=config_url,
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url,
            redirect_path=redirect_path,
            required_scopes=scopes.split(),
        )

        logger.info("✓ OAuth authentication provider initialized successfully")
        logger.info(
            "  MCP clients will auto-discover OAuth requirements and handle token management"
        )
        logger.info(
            f"  OAuth authorization endpoint: https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
        )
        logger.info(
            f"  OAuth token endpoint: https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        )

        return auth_provider

    except Exception as e:
        logger.error(f"Failed to initialize OAuth authentication provider: {e!s}", exc_info=True)
        logger.warning("Server will operate without OAuth capability broadcasting")
        return None
