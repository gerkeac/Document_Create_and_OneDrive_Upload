"""Main MCP server implementation."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from mcp_document_server.generators.word_generator import WordGenerator

# Initialize FastMCP server
mcp = FastMCP("Document Generator")

# Create a temporary directory for generated files
TEMP_DIR = Path(tempfile.gettempdir()) / "mcp_documents"
TEMP_DIR.mkdir(exist_ok=True)


@mcp.tool()  # type: ignore[misc]
def create_word_document(
    content: str,
    format: str = "markdown",
    filename: str | None = None,
    upload_to_onedrive: bool = False,
    onedrive_path: str = "/Documents/LibreChat",
    title: str | None = None,
    author: str | None = None,
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
        # Validate format
        if format not in ["markdown", "json"]:
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
            result_path = generator.generate_from_markdown(
                content=content,
                output_path=output_path,
                title=title,
                author=author,
            )
        else:  # json
            try:
                json_content = json.loads(content)
            except json.JSONDecodeError as e:
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
            response["message"] += " (OneDrive upload not implemented yet - Phase 2)"
            response["onedrive_path"] = onedrive_path

        return response

    except Exception as e:
        return {
            "success": False,
            "message": f"Error generating document: {e!s}",
            "error_type": type(e).__name__,
        }


if __name__ == "__main__":
    # Run the server
    mcp.run()
