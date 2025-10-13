"""Tests for Word document generation."""

import pytest
from mcp_document_server.generators import WordGenerator


def test_word_generator_initialization() -> None:
    """Test that WordGenerator can be initialized."""
    generator = WordGenerator()
    assert generator is not None


@pytest.mark.skip(reason="Not implemented yet - Phase 1")
def test_generate_from_markdown() -> None:
    """Test generating Word document from markdown."""
    # TODO: Implement in Phase 1
    pass


@pytest.mark.skip(reason="Not implemented yet - Phase 1")
def test_generate_from_json() -> None:
    """Test generating Word document from JSON."""
    # TODO: Implement in Phase 1
    pass
