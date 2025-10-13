"""Main MCP server implementation."""

import json
import logging
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.server import Context

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
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Document Generator")

# Create a temporary directory for generated files
TEMP_DIR = Path(tempfile.gettempdir()) / "mcp_documents"
TEMP_DIR.mkdir(exist_ok=True)

# Track server start time for uptime
SERVER_START_TIME = time.time()


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
                # Extract OAuth token from request headers
                if not ctx or not hasattr(ctx, "meta") or not ctx.meta:
                    raise ValueError(
                        "OneDrive upload requires OAuth authentication. "
                        "No request context available. "
                        "Ensure LibreChat is configured to pass OAuth tokens."
                    )

                # Get headers from context
                headers = ctx.meta.get("headers", {}) if isinstance(ctx.meta, dict) else {}

                if not headers:
                    logger.warning("No headers found in request context, trying environment")
                    # Fallback: check if token is in environment (for testing)
                    test_token = os.environ.get("MICROSOFT_ACCESS_TOKEN")
                    if test_token:
                        logger.info("Using test token from environment")
                        headers = {"Authorization": f"Bearer {test_token}"}
                    else:
                        raise ValueError(
                            "OneDrive upload requires OAuth authentication. "
                            "Missing Authorization header. "
                            "Please authenticate via LibreChat."
                        )

                # Extract and validate token
                token_data = TokenExtractor.extract_from_headers(headers)

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
                # Extract OAuth token from request headers
                if not ctx or not hasattr(ctx, "meta") or not ctx.meta:
                    raise ValueError(
                        "OneDrive upload requires OAuth authentication. "
                        "No request context available."
                    )

                # Get headers from context
                headers = ctx.meta.get("headers", {}) if isinstance(ctx.meta, dict) else {}

                if not headers:
                    logger.warning("No headers found in request context, trying environment")
                    test_token = os.environ.get("MICROSOFT_ACCESS_TOKEN")
                    if test_token:
                        logger.info("Using test token from environment")
                        headers = {"Authorization": f"Bearer {test_token}"}
                    else:
                        raise ValueError(
                            "OneDrive upload requires OAuth authentication. "
                            "Missing Authorization header."
                        )

                # Extract and validate token
                token_data = TokenExtractor.extract_from_headers(headers)

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
                # Extract OAuth token from request headers
                if not ctx or not hasattr(ctx, "meta") or not ctx.meta:
                    raise ValueError(
                        "OneDrive upload requires OAuth authentication. "
                        "No request context available."
                    )

                # Get headers from context
                headers = ctx.meta.get("headers", {}) if isinstance(ctx.meta, dict) else {}

                if not headers:
                    logger.warning("No headers found in request context, trying environment")
                    test_token = os.environ.get("MICROSOFT_ACCESS_TOKEN")
                    if test_token:
                        logger.info("Using test token from environment")
                        headers = {"Authorization": f"Bearer {test_token}"}
                    else:
                        raise ValueError(
                            "OneDrive upload requires OAuth authentication. "
                            "Missing Authorization header."
                        )

                # Extract and validate token
                token_data = TokenExtractor.extract_from_headers(headers)

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

        # Extract OAuth token from request headers
        if not ctx or not hasattr(ctx, "meta") or not ctx.meta:
            raise ValueError(
                "OneDrive access requires OAuth authentication. " "No request context available."
            )

        # Get headers from context
        headers = ctx.meta.get("headers", {}) if isinstance(ctx.meta, dict) else {}

        if not headers:
            # Fallback for testing
            test_token = os.environ.get("MICROSOFT_ACCESS_TOKEN")
            if test_token:
                logger.info("Using test token from environment")
                headers = {"Authorization": f"Bearer {test_token}"}
            else:
                raise ValueError("Missing Authorization header. Please authenticate via LibreChat.")

        # Extract and validate token
        token_data = TokenExtractor.extract_from_headers(headers)

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
    # Run the server
    mcp.run()
