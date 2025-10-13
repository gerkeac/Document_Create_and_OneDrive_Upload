"""Pytest configuration and fixtures."""

from typing import Any

import pytest


@pytest.fixture
def sample_markdown() -> str:
    """Sample markdown content for testing."""
    return """# Test Document

## Section 1
This is a test paragraph.

- Bullet point 1
- Bullet point 2

## Section 2
Another paragraph with **bold** and *italic* text.
"""


@pytest.fixture
def sample_json_document() -> dict[str, Any]:
    """Sample JSON document structure for testing."""
    return {
        "title": "Test Document",
        "sections": [
            {
                "heading": "Section 1",
                "content": "This is a test paragraph.",
                "bullets": ["Bullet point 1", "Bullet point 2"],
            },
            {
                "heading": "Section 2",
                "content": "Another paragraph with formatting.",
            },
        ],
    }
