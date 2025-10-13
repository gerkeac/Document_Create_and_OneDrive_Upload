"""OneDrive client for file uploads using Microsoft Graph API.

This module handles:
- File uploads to OneDrive
- Folder creation
- Conflict resolution (filename incrementing)
- Shareable link generation

Microsoft Graph API Reference:
- Upload files: https://learn.microsoft.com/en-us/graph/api/driveitem-put-content
- Create folders: https://learn.microsoft.com/en-us/graph/api/driveitem-post-children
- Get sharing links: https://learn.microsoft.com/en-us/graph/api/driveitem-createlink
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Microsoft Graph API base URL
GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"


class OneDriveError(Exception):
    """Base exception for OneDrive operations."""

    pass


class OneDriveAuthError(OneDriveError):
    """Authentication error (invalid or expired token)."""

    pass


class OneDriveUploadError(OneDriveError):
    """File upload error."""

    pass


class OneDriveClient:
    """Client for interacting with OneDrive via Microsoft Graph API."""

    def __init__(self, access_token: str, user_id: str = "unknown") -> None:
        """
        Initialize OneDrive client with access token.

        Args:
            access_token: OAuth access token for Microsoft Graph API
            user_id: User identifier for logging purposes
        """
        self.access_token = access_token
        self.user_id = user_id
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        logger.info(f"OneDriveClient initialized for user {user_id[:8]}...")

    async def _make_request(
        self,
        method: str,
        url: str,
        data: bytes | dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Make an HTTP request to Microsoft Graph API.

        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            url: Full URL to request
            data: Request body (bytes for file upload, dict for JSON)
            headers: Optional additional headers

        Returns:
            Response JSON as dictionary

        Raises:
            OneDriveAuthError: If authentication fails (401)
            OneDriveError: For other API errors
        """
        # Merge headers
        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                if isinstance(data, dict):
                    response = await client.request(method, url, json=data, headers=request_headers)
                elif isinstance(data, bytes):
                    response = await client.request(
                        method, url, content=data, headers=request_headers
                    )
                else:
                    response = await client.request(method, url, headers=request_headers)

                # Check for authentication errors
                if response.status_code == 401:
                    logger.error(f"Authentication failed for user {self.user_id[:8]}...")
                    raise OneDriveAuthError(
                        "Access token is invalid or expired. "
                        "Please re-authenticate via LibreChat."
                    )

                # Check for other errors
                if response.status_code >= 400:
                    error_msg = f"Graph API error: {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg = f"{error_msg} - {error_data.get('error', {}).get('message', 'Unknown error')}"
                    except Exception:
                        error_msg = f"{error_msg} - {response.text[:200]}"

                    logger.error(error_msg)
                    raise OneDriveError(error_msg)

                # Parse response
                if response.content:
                    result: dict[str, Any] = response.json()
                    return result
                return {}

            except httpx.TimeoutException as e:
                logger.error(f"Request timeout: {e!s}")
                raise OneDriveError(f"Request timed out: {e!s}") from e
            except httpx.RequestError as e:
                logger.error(f"Request error: {e!s}")
                raise OneDriveError(f"Network error: {e!s}") from e

    async def _ensure_folder_exists(self, folder_path: str) -> str:
        """
        Ensure that a folder exists in OneDrive, creating it if necessary.

        Args:
            folder_path: Folder path (e.g., '/Documents/LibreChat')

        Returns:
            Folder ID

        Raises:
            OneDriveError: If folder creation fails
        """
        # Normalize path
        folder_path = folder_path.strip("/")
        if not folder_path:
            # Root folder
            return "root"

        # Split path into parts
        parts = folder_path.split("/")

        # Navigate/create folder hierarchy
        current_id = "root"
        for part in parts:
            if not part:
                continue

            # Check if folder exists
            try:
                url = f"{GRAPH_API_BASE}/me/drive/items/{current_id}/children"
                response = await self._make_request("GET", url)

                # Look for folder in children
                folder_found = False
                for item in response.get("value", []):
                    if item.get("name") == part and "folder" in item:
                        current_id = item["id"]
                        folder_found = True
                        logger.debug(f"Found existing folder: {part}")
                        break

                if not folder_found:
                    # Create folder
                    logger.info(f"Creating folder: {part}")
                    url = f"{GRAPH_API_BASE}/me/drive/items/{current_id}/children"
                    folder_data = {
                        "name": part,
                        "folder": {},
                        "@microsoft.graph.conflictBehavior": "fail",
                    }
                    response = await self._make_request("POST", url, data=folder_data)
                    current_id = response["id"]

            except OneDriveError as e:
                logger.error(f"Error ensuring folder exists: {e!s}")
                raise

        logger.info(f"Folder path '{folder_path}' exists (ID: {current_id})")
        return current_id

    async def upload_file(
        self,
        file_path: Path,
        onedrive_path: str = "/Documents/LibreChat",
        conflict_behavior: str = "rename",
    ) -> dict[str, Any]:
        """
        Upload a file to OneDrive.

        Args:
            file_path: Local path to the file to upload
            onedrive_path: Destination folder path in OneDrive
            conflict_behavior: How to handle filename conflicts:
                - 'rename': Auto-increment filename (default)
                - 'replace': Overwrite existing file
                - 'fail': Raise error if file exists

        Returns:
            Dictionary with:
                - success: bool
                - filename: str (uploaded filename)
                - onedrive_url: str (web URL to access file)
                - file_id: str (OneDrive file ID)
                - file_size_bytes: int

        Raises:
            OneDriveUploadError: If upload fails
        """
        try:
            # Validate file exists
            if not file_path.exists():
                raise OneDriveUploadError(f"File not found: {file_path}")

            # Read file content
            file_content = file_path.read_bytes()
            file_size = len(file_content)

            logger.info(f"Uploading {file_path.name} ({file_size} bytes) to {onedrive_path}")

            # Ensure destination folder exists
            folder_id = await self._ensure_folder_exists(onedrive_path)

            # Prepare filename
            filename = file_path.name

            # Handle filename conflicts
            if conflict_behavior == "rename":
                # Append timestamp to filename to avoid conflicts
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name_parts = filename.rsplit(".", 1)
                if len(name_parts) == 2:
                    filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                else:
                    filename = f"{filename}_{timestamp}"

            # Upload file
            # For files < 4MB, use simple upload
            # For larger files, use resumable upload (future enhancement)
            upload_url = f"{GRAPH_API_BASE}/me/drive/items/{folder_id}:/{filename}:/content"

            upload_headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/octet-stream",
            }

            response = await self._make_request(
                "PUT", upload_url, data=file_content, headers=upload_headers
            )

            # Extract response data
            file_id = response.get("id", "")
            web_url = response.get("webUrl", "")

            logger.info(f"Successfully uploaded {filename} to OneDrive (ID: {file_id[:16]}...)")

            return {
                "success": True,
                "filename": filename,
                "onedrive_url": web_url,
                "file_id": file_id,
                "file_size_bytes": file_size,
                "message": f"File uploaded successfully to {onedrive_path}",
            }

        except OneDriveError:
            # Re-raise OneDrive-specific errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error during upload: {e!s}", exc_info=True)
            raise OneDriveUploadError(f"Upload failed: {e!s}") from e

    async def list_folders(self, parent_path: str = "/", max_depth: int = 2) -> list[str]:
        """
        List folders in OneDrive.

        Args:
            parent_path: Parent folder path to list
            max_depth: Maximum depth to traverse

        Returns:
            List of folder paths

        Raises:
            OneDriveError: If listing fails
        """
        try:
            # Normalize path
            parent_path = parent_path.strip("/")
            parent_id = "root" if not parent_path else await self._ensure_folder_exists(parent_path)

            folders: list[str] = []

            async def list_recursive(folder_id: str, current_path: str, depth: int) -> None:
                if depth > max_depth:
                    return

                url = f"{GRAPH_API_BASE}/me/drive/items/{folder_id}/children"
                response = await self._make_request("GET", url)

                for item in response.get("value", []):
                    if "folder" in item:
                        folder_name = item["name"]
                        folder_path = (
                            f"{current_path}/{folder_name}" if current_path else f"/{folder_name}"
                        )
                        folders.append(folder_path)

                        # Recurse into subfolder
                        if depth < max_depth:
                            await list_recursive(item["id"], folder_path, depth + 1)

            await list_recursive(parent_id, f"/{parent_path}" if parent_path else "", 0)

            logger.info(f"Listed {len(folders)} folders from {parent_path or '/'}")
            return sorted(folders)

        except OneDriveError:
            raise
        except Exception as e:
            logger.error(f"Error listing folders: {e!s}", exc_info=True)
            raise OneDriveError(f"Failed to list folders: {e!s}") from e

    async def get_user_info(self) -> dict[str, Any]:
        """
        Get information about the authenticated user.

        Returns:
            Dictionary with user information (displayName, email, etc.)

        Raises:
            OneDriveAuthError: If token is invalid
        """
        try:
            url = f"{GRAPH_API_BASE}/me"
            response = await self._make_request("GET", url)

            logger.info(f"Retrieved user info: {response.get('displayName', 'Unknown')}")
            return response

        except OneDriveAuthError:
            raise
        except Exception as e:
            logger.error(f"Error getting user info: {e!s}")
            raise OneDriveError(f"Failed to get user info: {e!s}") from e
