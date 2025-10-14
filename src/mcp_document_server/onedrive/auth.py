"""OAuth authentication and token management for OneDrive integration.

This module handles:
- Extracting OAuth tokens from HTTP headers (passed by LibreChat)
- Validating access tokens
- Token expiration checking
- User identification from tokens

LibreChat OAuth Flow:
1. User authenticates via LibreChat UI (OAuth popup)
2. LibreChat stores encrypted tokens per-user
3. LibreChat passes tokens in HTTP headers with each MCP request:
   - Authorization: Bearer <access_token>
   - X-User-ID: <librechat_user_id>
4. This module extracts and validates tokens from headers
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TokenExtractor:
    """Extract and validate OAuth tokens from MCP request headers."""

    @staticmethod
    def extract_from_headers(headers: dict[str, Any]) -> dict[str, str]:
        """
        Extract OAuth access token from HTTP headers.

        LibreChat passes OAuth tokens in the Authorization header:
        Authorization: Bearer <access_token>

        Args:
            headers: Dictionary of HTTP headers from MCP request

        Returns:
            Dictionary with:
                - access_token: OAuth access token
                - user_id: LibreChat user ID (for multi-user isolation)

        Raises:
            ValueError: If required headers are missing or malformed
        """
        # Debug: Log all header keys received
        logger.debug(f"Extracting token from {len(headers)} header(s)")
        logger.debug(f"Header keys received: {list(headers.keys())}")

        # Extract Authorization header
        auth_header = headers.get("authorization") or headers.get("Authorization")

        if not auth_header:
            logger.error("Authorization header not found")
            logger.debug(
                f"Searched for 'authorization' and 'Authorization' in: {list(headers.keys())}"
            )
            raise ValueError(
                "Missing Authorization header. "
                "Ensure LibreChat is configured to pass OAuth tokens to this MCP server."
            )

        logger.debug(f"Authorization header found, length: {len(auth_header)}")

        # Parse Bearer token
        if not auth_header.startswith("Bearer "):
            logger.error(f"Invalid Authorization format: {auth_header[:30]}...")
            raise ValueError("Invalid Authorization header format. Expected 'Bearer <token>'.")

        access_token = auth_header.replace("Bearer ", "", 1).strip()

        if not access_token:
            logger.error("Authorization header contains 'Bearer ' but no token")
            raise ValueError("Empty access token in Authorization header.")

        # Extract user ID (for multi-user support)
        user_id = headers.get("x-user-id") or headers.get("X-User-ID") or "unknown"

        # Mask token for security logging
        token_preview = (
            access_token[:10] + "..." + access_token[-8:] if len(access_token) > 20 else "[short]"
        )

        logger.info(
            f"✓ Successfully extracted OAuth token for user: {user_id[:8]}... "
            f"(token length: {len(access_token)}, preview: {token_preview})"
        )
        logger.debug(f"Token starts with: {access_token[:20]}...")

        return {
            "access_token": access_token,
            "user_id": user_id,
        }

    @staticmethod
    def validate_token_format(token: str) -> bool:
        """
        Validate that a token has the expected format.

        Microsoft OAuth tokens are typically:
        - Base64-encoded strings
        - Length: 1000-2000 characters
        - Contains letters, numbers, and special characters

        Args:
            token: Access token to validate

        Returns:
            True if token format is valid

        Raises:
            ValueError: If token format is invalid
        """
        if not token or not isinstance(token, str):
            raise ValueError("Token must be a non-empty string")

        # Basic length check
        if len(token) < 50:
            raise ValueError(
                f"Token too short ({len(token)} chars). "
                "Expected OAuth token length > 50 characters."
            )

        # Check for suspicious patterns
        if token.count(" ") > 2:
            raise ValueError("Token contains too many spaces. May be malformed.")

        logger.debug(f"Token format validation passed (length: {len(token)})")
        return True


class TokenManager:
    """
    Manage OAuth tokens with encryption and refresh logic.

    Note: LibreChat handles token refresh automatically when refresh tokens are available.
    This manager focuses on token validation and extraction.
    """

    def __init__(self, encryption_key: str | None = None) -> None:
        """
        Initialize token manager.

        Args:
            encryption_key: Key for encrypting tokens at rest (optional for Phase 2)
        """
        self.encryption_key = encryption_key
        logger.info("TokenManager initialized")

    def validate_token(self, token: str) -> bool:
        """
        Validate an OAuth access token.

        This performs basic validation checks. Full validation happens
        when the token is used with Microsoft Graph API.

        Args:
            token: Access token to validate

        Returns:
            True if token passes basic validation

        Raises:
            ValueError: If token is invalid
        """
        try:
            TokenExtractor.validate_token_format(token)
            return True
        except ValueError as e:
            logger.error(f"Token validation failed: {e!s}")
            raise

    def extract_from_request_headers(self, headers: dict[str, Any]) -> dict[str, str]:
        """
        Extract and validate OAuth token from MCP request headers.

        This is the main entry point for token extraction.

        Args:
            headers: HTTP headers from MCP request

        Returns:
            Dictionary with access_token and user_id

        Raises:
            ValueError: If token extraction or validation fails
        """
        # Extract token
        token_data = TokenExtractor.extract_from_headers(headers)

        # Validate token format
        self.validate_token(token_data["access_token"])

        logger.info(f"Successfully validated token for user {token_data['user_id'][:8]}...")

        return token_data
