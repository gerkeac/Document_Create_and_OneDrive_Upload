"""Integration tests for MCP server."""

import json
from pathlib import Path

import pytest
from fastmcp import Client
from mcp.types import TextContent
from mcp_document_server.server import mcp


@pytest.mark.asyncio
async def test_server_lists_tools() -> None:
    """Test that server exposes the create_word_document tool."""
    async with Client(mcp) as client:
        tools = await client.list_tools()

        assert len(tools) >= 1

        # Find create_word_document tool
        word_tool = None
        for tool in tools:
            if tool.name == "create_word_document":
                word_tool = tool
                break

        assert word_tool is not None
        assert "Generate a Word document" in word_tool.description
        assert word_tool.inputSchema is not None


@pytest.mark.asyncio
async def test_create_word_document_markdown() -> None:
    """Test creating a Word document from markdown."""
    async with Client(mcp) as client:
        markdown_content = """# Test Document

This is a **test** document with *formatting*.

## Section 1

- Item 1
- Item 2
- Item 3"""

        result = await client.call_tool(
            "create_word_document",
            arguments={
                "content": markdown_content,
                "format": "markdown",
                "filename": "test_markdown_doc",
            },
        )

        assert len(result.content) > 0
        assert isinstance(result.content[0], TextContent)

        response = json.loads(result.content[0].text)
        assert response["success"] is True
        assert response["filename"] == "test_markdown_doc.docx"
        assert response["file_size_bytes"] > 0
        assert "local_path" in response

        # Verify file exists
        local_path = Path(response["local_path"])
        assert local_path.exists()

        # Cleanup
        local_path.unlink()


@pytest.mark.asyncio
async def test_create_word_document_json() -> None:
    """Test creating a Word document from JSON."""
    async with Client(mcp) as client:
        json_content = {
            "title": "JSON Test Document",
            "author": "Test Suite",
            "blocks": [
                {"type": "heading", "level": 1, "text": "Main Title"},
                {"type": "paragraph", "text": "This is a paragraph."},
                {
                    "type": "list",
                    "list_type": "bullet",
                    "items": ["First", "Second", "Third"],
                },
            ],
        }

        result = await client.call_tool(
            "create_word_document",
            arguments={
                "content": json.dumps(json_content),
                "format": "json",
                "filename": "test_json_doc",
            },
        )

        assert len(result.content) > 0
        response = json.loads(result.content[0].text)
        assert response["success"] is True
        assert response["filename"] == "test_json_doc.docx"

        # Verify file exists
        local_path = Path(response["local_path"])
        assert local_path.exists()

        # Cleanup
        local_path.unlink()


@pytest.mark.asyncio
async def test_create_word_document_auto_filename() -> None:
    """Test creating a Word document with auto-generated filename."""
    async with Client(mcp) as client:
        result = await client.call_tool(
            "create_word_document",
            arguments={
                "content": "# Simple Document",
                "format": "markdown",
            },
        )

        response = json.loads(result.content[0].text)
        assert response["success"] is True
        assert response["filename"].startswith("document_")
        assert response["filename"].endswith(".docx")

        # Cleanup
        local_path = Path(response["local_path"])
        if local_path.exists():
            local_path.unlink()


@pytest.mark.asyncio
async def test_create_word_document_with_metadata() -> None:
    """Test creating a Word document with title and author metadata."""
    async with Client(mcp) as client:
        result = await client.call_tool(
            "create_word_document",
            arguments={
                "content": "# Test Document\n\nContent here.",
                "format": "markdown",
                "filename": "metadata_test",
                "title": "My Document Title",
                "author": "John Doe",
            },
        )

        response = json.loads(result.content[0].text)
        assert response["success"] is True

        # Cleanup
        local_path = Path(response["local_path"])
        if local_path.exists():
            local_path.unlink()


@pytest.mark.asyncio
async def test_create_word_document_invalid_format() -> None:
    """Test error handling for invalid format."""
    async with Client(mcp) as client:
        result = await client.call_tool(
            "create_word_document",
            arguments={
                "content": "# Test",
                "format": "invalid_format",
            },
        )

        response = json.loads(result.content[0].text)
        assert response["success"] is False
        assert "Invalid format" in response["message"]


@pytest.mark.asyncio
async def test_create_word_document_invalid_json() -> None:
    """Test error handling for invalid JSON content."""
    async with Client(mcp) as client:
        result = await client.call_tool(
            "create_word_document",
            arguments={
                "content": "not valid json {]",
                "format": "json",
            },
        )

        response = json.loads(result.content[0].text)
        assert response["success"] is False
        assert "Invalid JSON" in response["message"]


@pytest.mark.asyncio
async def test_create_word_document_onedrive_placeholder() -> None:
    """Test OneDrive upload flag (Phase 2 placeholder)."""
    async with Client(mcp) as client:
        result = await client.call_tool(
            "create_word_document",
            arguments={
                "content": "# Test Document",
                "format": "markdown",
                "filename": "onedrive_test",
                "upload_to_onedrive": True,
                "onedrive_path": "/Documents/Test",
            },
        )

        response = json.loads(result.content[0].text)
        assert response["success"] is True
        assert "not implemented yet" in response["message"].lower()
        assert response["onedrive_path"] == "/Documents/Test"

        # Cleanup
        local_path = Path(response["local_path"])
        if local_path.exists():
            local_path.unlink()


@pytest.mark.asyncio
async def test_create_word_document_complex_markdown() -> None:
    """Test creating a complex Word document with multiple elements."""
    async with Client(mcp) as client:
        markdown = """# Annual Report 2025

## Executive Summary

This report shows **strong growth** in Q4.

## Key Achievements

- Launched 3 new features
- Increased user base by *40%*
- Improved response time

## Financial Data

| Quarter | Revenue | Growth |
|---------|---------|--------|
| Q1      | $250K   | 20%    |
| Q2      | $300K   | 25%    |

## Next Steps

1. Expand team
2. Launch product
3. Enter new markets"""

        result = await client.call_tool(
            "create_word_document",
            arguments={
                "content": markdown,
                "format": "markdown",
                "filename": "complex_report",
                "title": "Annual Report",
                "author": "Test Company",
            },
        )

        response = json.loads(result.content[0].text)
        assert response["success"] is True
        assert response["file_size_bytes"] > 5000  # Complex document should be larger

        # Cleanup
        local_path = Path(response["local_path"])
        if local_path.exists():
            local_path.unlink()
