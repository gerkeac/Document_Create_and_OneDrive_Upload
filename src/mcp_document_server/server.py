"""Main MCP server implementation."""

import json
import logging
import os
import tempfile
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.server import Context
from starlette.responses import JSONResponse

from mcp_document_server.auth import create_auth_provider
from mcp_document_server.generators.excel_generator import ExcelGenerator
from mcp_document_server.generators.powerpoint_generator import PowerPointGenerator
from mcp_document_server.generators.word_generator import WordGenerator
from mcp_document_server.onedrive import (
    OneDriveAuthError,
    OneDriveClient,
    OneDriveError,
    TokenExtractor,
)

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
log_file = os.environ.get("LOG_FILE", None)
# Log rotation settings (configurable via environment variables)
log_max_bytes = int(os.environ.get("LOG_MAX_BYTES", 10 * 1024 * 1024))  # 10MB default
log_backup_count = int(os.environ.get("LOG_BACKUP_COUNT", 5))  # Keep 5 backup files

handlers: list[logging.Handler] = [logging.StreamHandler()]

# Add rotating file handler if LOG_FILE is specified
if log_file:
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Use RotatingFileHandler to prevent unlimited log growth
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=log_max_bytes,
        backupCount=log_backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    handlers.append(file_handler)

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=handlers,
)
logger = logging.getLogger(__name__)

# Log startup information
if log_file:
    logger.info(f"File logging enabled: {log_file}")
    logger.info(
        f"Log rotation: {log_max_bytes / 1024 / 1024:.1f}MB per file, {log_backup_count} backups"
    )
    logger.info(
        f"Maximum disk usage for logs: ~{(log_max_bytes * (log_backup_count + 1)) / 1024 / 1024:.1f}MB"
    )
logger.info(f"Log level set to: {log_level}")

# Initialize OAuth authentication provider (if configured)
# This enables MCP protocol-level OAuth capability broadcasting
auth_provider = create_auth_provider()

# Initialize FastMCP server with optional authentication
if auth_provider:
    logger.info("Initializing FastMCP server with OAuth capability broadcasting")
    mcp = FastMCP("Document Generator", auth=auth_provider)

    # Add RFC 9728 OAuth Protected Resource Metadata endpoint
    # This is required by MCP protocol but not provided by FastMCP's OIDCProxy
    @mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])  # type: ignore[misc]
    def oauth_protected_resource_metadata(request: Any) -> JSONResponse:
        """
        OAuth 2.0 Protected Resource Metadata (RFC 9728).

        Provides authorization server information for MCP clients to discover
        where to obtain access tokens for this protected resource.

        Args:
            request: Starlette Request object (required by FastMCP custom routes)

        Returns:
            JSONResponse with authorization_servers list
        """
        base_url = os.environ.get("MCP_BASE_URL", "http://localhost:3000")

        # Return metadata pointing to our OAuth authorization server
        metadata = {
            "resource": base_url,
            "authorization_servers": [base_url],
            # Optional: specify required scopes
            "scopes_supported": ["Files.ReadWrite", "User.Read", "offline_access"],
            "bearer_methods_supported": ["header"],
            "resource_documentation": f"{base_url}/docs",
        }

        return JSONResponse(metadata)

    logger.info("✓ Added OAuth protected resource metadata endpoint")
else:
    logger.info(
        "Initializing FastMCP server in passthrough mode (no OAuth capability broadcasting)"
    )
    mcp = FastMCP("Document Generator")

# Create a temporary directory for generated files
TEMP_DIR = Path(tempfile.gettempdir()) / "mcp_documents"
TEMP_DIR.mkdir(exist_ok=True)

# Track server start time for uptime
SERVER_START_TIME = time.time()


def extract_oauth_token(ctx: Context | None) -> dict[str, str]:
    """
    Extract OAuth access token from request context.

    When FastMCP auth is enabled, tokens are automatically validated and available
    in ctx.meta. When auth is disabled (passthrough mode), tokens are extracted
    from Authorization headers.

    Args:
        ctx: Request context from FastMCP

    Returns:
        Dictionary with 'access_token' and 'user_id'

    Raises:
        ValueError: If OAuth token is not available or invalid
        OneDriveAuthError: If authentication fails
    """
    if not ctx or not hasattr(ctx, "meta") or not ctx.meta:
        logger.error("No request context available for OAuth token extraction")
        raise ValueError(
            "OneDrive upload requires OAuth authentication. "
            "No request context available. "
            "Ensure LibreChat is configured to pass OAuth tokens."
        )

    # Log context structure for debugging
    logger.debug(f"Context meta type: {type(ctx.meta)}")
    logger.debug(
        f"Context meta keys: {list(ctx.meta.keys()) if isinstance(ctx.meta, dict) else 'Not a dict'}"
    )

    # Check if we have validated OAuth user info (when auth is enabled)
    if isinstance(ctx.meta, dict) and "user" in ctx.meta:
        logger.info("OAuth token validated by FastMCP auth provider")
        user_info = ctx.meta["user"]
        logger.debug(
            f"User info keys: {list(user_info.keys()) if isinstance(user_info, dict) else 'Not a dict'}"
        )

        # Extract access token from validated OAuth context
        # The OIDCProxy stores the access token in the user context
        if "access_token" in user_info:
            access_token = user_info["access_token"]
            user_id = user_info.get("sub") or user_info.get("oid") or user_info.get("id", "unknown")

            logger.info(
                f"✓ OAuth token extracted from authenticated context for user: {user_id[:8]}..."
            )
            return {"access_token": access_token, "user_id": user_id}

    # Fallback: Extract from headers (passthrough mode or LibreChat manual config)
    headers = ctx.meta.get("headers", {}) if isinstance(ctx.meta, dict) else {}

    if headers:
        logger.info(f"Received {len(headers)} header(s) from request")
        logger.debug(f"Header keys (case-sensitive): {list(headers.keys())}")

        # Check for Authorization header (case-insensitive)
        auth_header = headers.get("authorization") or headers.get("Authorization")
        if auth_header:
            # Mask token for security but show it exists
            if auth_header.startswith("Bearer "):
                token_preview = (
                    auth_header[7:17] + "..." + auth_header[-8:]
                    if len(auth_header) > 50
                    else "[too short]"
                )
                logger.info(f"✓ Authorization header found: Bearer {token_preview}")
                logger.debug(f"Token length: {len(auth_header) - 7} chars")
            else:
                logger.warning(
                    f"Authorization header present but doesn't start with 'Bearer ': {auth_header[:20]}..."
                )
        else:
            logger.warning("✗ No Authorization header found in request")
            logger.debug(f"Available headers: {', '.join(headers.keys())}")

        # Check for user ID header
        user_id_header = headers.get("x-user-id") or headers.get("X-User-ID")
        if user_id_header:
            logger.info(f"✓ User-ID header found: {user_id_header[:8]}...")
        else:
            logger.warning("✗ No X-User-ID header found in request")

        # Attempt token extraction using existing TokenExtractor
        if headers:
            try:
                token_data = TokenExtractor.extract_from_headers(headers)
                logger.info(
                    f"✓ OAuth token extracted from headers for user: {token_data['user_id'][:8]}..."
                )
                return token_data
            except Exception as e:
                logger.error(f"Failed to extract token from headers: {e!s}")

    # Final fallback: check environment for testing
    logger.warning("Attempting fallback to environment variable")
    test_token = os.environ.get("MICROSOFT_ACCESS_TOKEN")
    if test_token:
        logger.info("Using test token from environment")
        return {"access_token": test_token, "user_id": "test-user"}

    raise ValueError(
        "OneDrive upload requires OAuth authentication. "
        "Missing Authorization header or authenticated OAuth context. "
        "Please authenticate via LibreChat."
    )


@mcp.tool()  # type: ignore[misc]
def health_check() -> dict[str, Any]:
    """
    Check the health and status of the MCP Document Generator server.

    Returns:
        Dictionary with server health status, uptime, and version information
    """
    try:
        uptime_seconds = int(time.time() - SERVER_START_TIME)

        # Check if temp directory is accessible
        temp_accessible = TEMP_DIR.exists() and TEMP_DIR.is_dir()

        # Count files in temp directory
        file_count = len(list(TEMP_DIR.glob("*.docx"))) if temp_accessible else 0

        status = "healthy" if temp_accessible else "degraded"

        logger.info(f"Health check performed - Status: {status}, Uptime: {uptime_seconds}s")

        return {
            "status": status,
            "uptime_seconds": uptime_seconds,
            "version": "0.3.0",
            "phase": "Phase 3 - Full Office Suite",
            "temp_directory": str(TEMP_DIR),
            "temp_directory_accessible": temp_accessible,
            "cached_files": file_count,
            "message": "MCP Document Generator server is operational",
        }
    except Exception as e:
        logger.error(f"Health check failed: {e!s}")
        return {
            "status": "unhealthy",
            "message": f"Health check error: {e!s}",
            "error_type": type(e).__name__,
        }


@mcp.tool()  # type: ignore[misc]
async def create_word_document(
    content: str,
    format: str = "markdown",
    filename: str | None = None,
    upload_to_onedrive: bool = False,
    onedrive_path: str = "/Documents/LibreChat",
    title: str | None = None,
    author: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """
    Generate a Word document from markdown or JSON content.

    Args:
        content: Markdown or JSON string containing document content
        format: Input format ('markdown' or 'json')
        filename: Desired filename without extension
        upload_to_onedrive: Whether to upload to OneDrive after creation
        onedrive_path: OneDrive folder path (e.g., '/Documents/Reports')
        title: Optional document title for metadata
        author: Optional document author for metadata

    Returns:
        Dictionary with success status, filename, OneDrive URL, and file size
    """
    try:
        logger.info(f"Creating Word document - Format: {format}, Filename: {filename}")

        # Validate format
        if format not in ["markdown", "json"]:
            logger.warning(f"Invalid format requested: {format}")
            return {
                "success": False,
                "message": f"Invalid format '{format}'. Must be 'markdown' or 'json'.",
            }

        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"document_{timestamp}"

        # Ensure filename doesn't have extension
        if filename.endswith(".docx"):
            filename = filename[:-5]

        # Create output path
        output_path = TEMP_DIR / f"{filename}.docx"

        # Initialize generator
        generator = WordGenerator()

        # Generate document based on format
        if format == "markdown":
            logger.debug(f"Generating document from markdown (length: {len(content)} chars)")
            result_path = generator.generate_from_markdown(
                content=content,
                output_path=output_path,
                title=title,
                author=author,
            )
        else:  # json
            try:
                json_content = json.loads(content)
                logger.debug(f"Parsed JSON content with {len(json_content)} top-level keys")
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e!s}")
                return {
                    "success": False,
                    "message": f"Invalid JSON content: {e!s}",
                }

            result_path = generator.generate_from_json(
                content=json_content,
                output_path=output_path,
            )

        # Get file size
        file_size = result_path.stat().st_size

        logger.info(f"Document created successfully: {result_path.name} ({file_size} bytes)")

        # Prepare response
        response: dict[str, Any] = {
            "success": True,
            "filename": result_path.name,
            "local_path": str(result_path),
            "file_size_bytes": file_size,
            "message": "Document created successfully",
        }

        # Handle OneDrive upload (Phase 2)
        if upload_to_onedrive:
            logger.info(f"OneDrive upload requested for path: {onedrive_path}")

            try:
                # Extract OAuth token (handles both auth-enabled and passthrough modes)
                token_data = extract_oauth_token(ctx)

                # Create OneDrive client
                onedrive_client = OneDriveClient(
                    access_token=token_data["access_token"],
                    user_id=token_data["user_id"],
                )

                # Upload file
                upload_result = await onedrive_client.upload_file(
                    file_path=result_path,
                    onedrive_path=onedrive_path,
                    conflict_behavior="rename",
                )

                # Merge upload result into response
                response.update(
                    {
                        "onedrive_url": upload_result.get("onedrive_url"),
                        "onedrive_file_id": upload_result.get("file_id"),
                        "onedrive_filename": upload_result.get("filename"),
                        "message": "Document created and uploaded to OneDrive successfully",
                    }
                )

                logger.info(f"Document uploaded to OneDrive: {upload_result.get('filename')}")

            except (ValueError, OneDriveAuthError) as e:
                logger.error(f"Authentication error during OneDrive upload: {e!s}")
                response["onedrive_error"] = str(e)
                response["message"] += (
                    " | OneDrive upload failed: Authentication error. "
                    "Please re-authenticate via LibreChat."
                )
            except OneDriveError as e:
                logger.error(f"OneDrive upload error: {e!s}")
                response["onedrive_error"] = str(e)
                response["message"] += f" | OneDrive upload failed: {e!s}"
            except Exception as e:
                logger.error(f"Unexpected error during OneDrive upload: {e!s}", exc_info=True)
                response["onedrive_error"] = f"Unexpected error: {e!s}"
                response["message"] += " | OneDrive upload failed (unexpected error)"

        return response

    except Exception as e:
        logger.error(f"Error generating document: {e!s}", exc_info=True)
        return {
            "success": False,
            "message": f"Error generating document: {e!s}",
            "error_type": type(e).__name__,
        }


@mcp.tool()  # type: ignore[misc]
async def create_powerpoint_presentation(
    slides: list[dict[str, Any]],
    filename: str | None = None,
    theme: str = "default",
    upload_to_onedrive: bool = False,
    onedrive_path: str = "/Documents/LibreChat",
    ctx: Context | None = None,
) -> dict[str, Any]:
    """
    Generate a PowerPoint presentation from structured slide content.

    Args:
        slides: List of slide dictionaries with layout, title, content
        filename: Desired filename without extension
        theme: Theme name (default, blue, professional, minimal)
        upload_to_onedrive: Whether to upload to OneDrive after creation
        onedrive_path: OneDrive folder path (e.g., '/Documents/Presentations')
        ctx: Request context (for OAuth token extraction)

    Returns:
        Dictionary with success status, filename, OneDrive URL, slide count, and file size
    """
    try:
        logger.info(
            f"Creating PowerPoint presentation - Slides: {len(slides)}, "
            f"Theme: {theme}, Filename: {filename}"
        )

        # Validate input
        if not slides or not isinstance(slides, list):
            logger.warning("Invalid slides data provided")
            return {
                "success": False,
                "message": "slides parameter must be a non-empty list of slide objects",
            }

        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"presentation_{timestamp}"

        # Ensure filename doesn't have extension
        if filename.endswith(".pptx"):
            filename = filename[:-5]

        # Create output path
        output_path = TEMP_DIR / f"{filename}.pptx"

        # Initialize generator
        generator = PowerPointGenerator()

        # Generate presentation
        logger.debug(f"Generating presentation with {len(slides)} slides, theme={theme}")
        result_path = generator.generate_presentation(
            slides=slides,
            output_path=output_path,
            theme=theme,
        )

        # Get file size
        file_size = result_path.stat().st_size

        logger.info(f"Presentation created successfully: {result_path.name} ({file_size} bytes)")

        # Prepare response
        response: dict[str, Any] = {
            "success": True,
            "filename": result_path.name,
            "local_path": str(result_path),
            "slide_count": len(slides),
            "file_size_bytes": file_size,
            "message": "Presentation created successfully",
        }

        # Handle OneDrive upload
        if upload_to_onedrive:
            logger.info(f"OneDrive upload requested for path: {onedrive_path}")

            try:
                # Extract OAuth token (handles both auth-enabled and passthrough modes)
                token_data = extract_oauth_token(ctx)

                # Create OneDrive client
                onedrive_client = OneDriveClient(
                    access_token=token_data["access_token"],
                    user_id=token_data["user_id"],
                )

                # Upload file
                upload_result = await onedrive_client.upload_file(
                    file_path=result_path,
                    onedrive_path=onedrive_path,
                    conflict_behavior="rename",
                )

                # Merge upload result into response
                response.update(
                    {
                        "onedrive_url": upload_result.get("onedrive_url"),
                        "onedrive_file_id": upload_result.get("file_id"),
                        "onedrive_filename": upload_result.get("filename"),
                        "message": "Presentation created and uploaded to OneDrive successfully",
                    }
                )

                logger.info(f"Presentation uploaded to OneDrive: {upload_result.get('filename')}")

            except (ValueError, OneDriveAuthError) as e:
                logger.error(f"Authentication error during OneDrive upload: {e!s}")
                response["onedrive_error"] = str(e)
                response["message"] += " | OneDrive upload failed: Authentication error."
            except OneDriveError as e:
                logger.error(f"OneDrive upload error: {e!s}")
                response["onedrive_error"] = str(e)
                response["message"] += f" | OneDrive upload failed: {e!s}"
            except Exception as e:
                logger.error(f"Unexpected error during OneDrive upload: {e!s}", exc_info=True)
                response["onedrive_error"] = f"Unexpected error: {e!s}"
                response["message"] += " | OneDrive upload failed (unexpected error)"

        return response

    except Exception as e:
        logger.error(f"Error generating presentation: {e!s}", exc_info=True)
        return {
            "success": False,
            "message": f"Error generating presentation: {e!s}",
            "error_type": type(e).__name__,
        }


@mcp.tool()  # type: ignore[misc]
async def create_excel_spreadsheet(
    sheets: list[dict[str, Any]],
    filename: str | None = None,
    include_formulas: bool = True,
    upload_to_onedrive: bool = False,
    onedrive_path: str = "/Documents/LibreChat",
    ctx: Context | None = None,
) -> dict[str, Any]:
    """
    Generate an Excel spreadsheet from tabular data.

    Args:
        sheets: List of worksheet dictionaries with name, headers, and data
        filename: Desired filename without extension
        include_formulas: Whether to process formula strings (default: True)
        upload_to_onedrive: Whether to upload to OneDrive after creation
        onedrive_path: OneDrive folder path (e.g., '/Documents/Spreadsheets')
        ctx: Request context (for OAuth token extraction)

    Returns:
        Dictionary with success status, filename, OneDrive URL, sheet count, and file size
    """
    try:
        logger.info(
            f"Creating Excel spreadsheet - Sheets: {len(sheets)}, "
            f"Formulas: {include_formulas}, Filename: {filename}"
        )

        # Validate input
        if not sheets or not isinstance(sheets, list):
            logger.warning("Invalid sheets data provided")
            return {
                "success": False,
                "message": "sheets parameter must be a non-empty list of sheet objects",
            }

        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"spreadsheet_{timestamp}"

        # Ensure filename doesn't have extension
        if filename.endswith(".xlsx"):
            filename = filename[:-5]

        # Create output path
        output_path = TEMP_DIR / f"{filename}.xlsx"

        # Initialize generator
        generator = ExcelGenerator()

        # Generate spreadsheet
        logger.debug(f"Generating spreadsheet with {len(sheets)} sheet(s)")
        result_path = generator.generate_spreadsheet(
            sheets=sheets,
            output_path=output_path,
            include_formulas=include_formulas,
        )

        # Get file size
        file_size = result_path.stat().st_size

        # Count total rows across all sheets
        total_rows = sum(len(sheet.get("data", [])) for sheet in sheets)

        logger.info(f"Spreadsheet created successfully: {result_path.name} ({file_size} bytes)")

        # Prepare response
        response: dict[str, Any] = {
            "success": True,
            "filename": result_path.name,
            "local_path": str(result_path),
            "sheet_count": len(sheets),
            "total_rows": total_rows,
            "file_size_bytes": file_size,
            "message": "Spreadsheet created successfully",
        }

        # Handle OneDrive upload
        if upload_to_onedrive:
            logger.info(f"OneDrive upload requested for path: {onedrive_path}")

            try:
                # Extract OAuth token (handles both auth-enabled and passthrough modes)
                token_data = extract_oauth_token(ctx)

                # Create OneDrive client
                onedrive_client = OneDriveClient(
                    access_token=token_data["access_token"],
                    user_id=token_data["user_id"],
                )

                # Upload file
                upload_result = await onedrive_client.upload_file(
                    file_path=result_path,
                    onedrive_path=onedrive_path,
                    conflict_behavior="rename",
                )

                # Merge upload result into response
                response.update(
                    {
                        "onedrive_url": upload_result.get("onedrive_url"),
                        "onedrive_file_id": upload_result.get("file_id"),
                        "onedrive_filename": upload_result.get("filename"),
                        "message": "Spreadsheet created and uploaded to OneDrive successfully",
                    }
                )

                logger.info(f"Spreadsheet uploaded to OneDrive: {upload_result.get('filename')}")

            except (ValueError, OneDriveAuthError) as e:
                logger.error(f"Authentication error during OneDrive upload: {e!s}")
                response["onedrive_error"] = str(e)
                response["message"] += " | OneDrive upload failed: Authentication error."
            except OneDriveError as e:
                logger.error(f"OneDrive upload error: {e!s}")
                response["onedrive_error"] = str(e)
                response["message"] += f" | OneDrive upload failed: {e!s}"
            except Exception as e:
                logger.error(f"Unexpected error during OneDrive upload: {e!s}", exc_info=True)
                response["onedrive_error"] = f"Unexpected error: {e!s}"
                response["message"] += " | OneDrive upload failed (unexpected error)"

        return response

    except Exception as e:
        logger.error(f"Error generating spreadsheet: {e!s}", exc_info=True)
        return {
            "success": False,
            "message": f"Error generating spreadsheet: {e!s}",
            "error_type": type(e).__name__,
        }


@mcp.tool()  # type: ignore[misc]
async def list_onedrive_folders(
    parent_path: str = "/",
    max_depth: int = 2,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """
    List available folders in user's OneDrive (for path selection).

    Args:
        parent_path: Parent folder path to list (e.g., '/' for root)
        max_depth: Maximum folder depth to traverse (default: 2)
        ctx: Request context (for OAuth token extraction)

    Returns:
        Dictionary with success status and list of folder paths
    """
    try:
        logger.info(f"Listing OneDrive folders from: {parent_path}")

        # Extract OAuth token (handles both auth-enabled and passthrough modes)
        token_data = extract_oauth_token(ctx)

        # Create OneDrive client
        onedrive_client = OneDriveClient(
            access_token=token_data["access_token"],
            user_id=token_data["user_id"],
        )

        # List folders
        folders = await onedrive_client.list_folders(
            parent_path=parent_path,
            max_depth=max_depth,
        )

        logger.info(f"Successfully listed {len(folders)} folders")

        return {
            "success": True,
            "folders": folders,
            "parent_path": parent_path,
            "folder_count": len(folders),
            "message": f"Retrieved {len(folders)} folders from OneDrive",
        }

    except (ValueError, OneDriveAuthError) as e:
        logger.error(f"Authentication error: {e!s}")
        return {
            "success": False,
            "message": f"Authentication error: {e!s}",
            "error_type": "AuthenticationError",
        }
    except OneDriveError as e:
        logger.error(f"OneDrive error: {e!s}")
        return {
            "success": False,
            "message": f"OneDrive error: {e!s}",
            "error_type": "OneDriveError",
        }
    except Exception as e:
        logger.error(f"Error listing folders: {e!s}", exc_info=True)
        return {
            "success": False,
            "message": f"Error listing folders: {e!s}",
            "error_type": type(e).__name__,
        }


if __name__ == "__main__":
    # Check for HTTP mode via environment variables
    server_port = os.environ.get("MCP_SERVER_PORT")
    server_host = os.environ.get("MCP_SERVER_HOST", "0.0.0.0")

    if server_port:
        # Run in HTTP (streamable) mode for Docker deployment
        # Using 'http' transport (not 'sse') - recommended for production
        # Provides full bidirectional communication and better scalability
        logger.info(f"Starting MCP server in HTTP (streamable) mode on {server_host}:{server_port}")
        mcp.run(transport="http", port=int(server_port), host=server_host)
    else:
        # Run in STDIO mode for local development
        logger.info("Starting MCP server in STDIO mode")
        mcp.run()
