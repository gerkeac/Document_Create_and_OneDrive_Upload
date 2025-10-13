"""Tests for markdown parser."""

from mcp_document_server.utils.markdown_parser import (
    parse_inline_formatting,
    parse_markdown,
)


def test_parse_heading() -> None:
    """Test parsing markdown headings."""
    markdown = "# Heading 1\n## Heading 2\n### Heading 3"
    blocks = parse_markdown(markdown)

    assert len(blocks) == 3
    assert blocks[0] == {"type": "heading", "level": 1, "text": "Heading 1"}
    assert blocks[1] == {"type": "heading", "level": 2, "text": "Heading 2"}
    assert blocks[2] == {"type": "heading", "level": 3, "text": "Heading 3"}


def test_parse_paragraph() -> None:
    """Test parsing plain paragraphs."""
    markdown = "This is a paragraph.\nThis is another paragraph."
    blocks = parse_markdown(markdown)

    assert len(blocks) == 2
    assert blocks[0] == {"type": "paragraph", "text": "This is a paragraph."}
    assert blocks[1] == {"type": "paragraph", "text": "This is another paragraph."}


def test_parse_bullet_list() -> None:
    """Test parsing bulleted lists."""
    markdown = "- Item 1\n- Item 2\n- Item 3"
    blocks = parse_markdown(markdown)

    assert len(blocks) == 1
    assert blocks[0]["type"] == "list"
    assert blocks[0]["list_type"] == "bullet"
    assert blocks[0]["items"] == ["Item 1", "Item 2", "Item 3"]


def test_parse_numbered_list() -> None:
    """Test parsing numbered lists."""
    markdown = "1. First item\n2. Second item\n3. Third item"
    blocks = parse_markdown(markdown)

    assert len(blocks) == 1
    assert blocks[0]["type"] == "list"
    assert blocks[0]["list_type"] == "number"
    assert blocks[0]["items"] == ["First item", "Second item", "Third item"]


def test_parse_table() -> None:
    """Test parsing markdown tables."""
    markdown = """| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |"""
    blocks = parse_markdown(markdown)

    assert len(blocks) == 1
    assert blocks[0]["type"] == "table"
    assert blocks[0]["headers"] == ["Header 1", "Header 2", "Header 3"]
    assert len(blocks[0]["rows"]) == 2
    assert blocks[0]["rows"][0] == ["Cell 1", "Cell 2", "Cell 3"]
    assert blocks[0]["rows"][1] == ["Cell 4", "Cell 5", "Cell 6"]


def test_parse_mixed_content() -> None:
    """Test parsing mixed markdown content."""
    markdown = """# Main Title

This is a paragraph with some text.

## Section 1

- Bullet 1
- Bullet 2

## Section 2

1. Item one
2. Item two

| Name | Value |
|------|-------|
| A    | 1     |
| B    | 2     |"""

    blocks = parse_markdown(markdown)

    # Verify structure
    assert blocks[0] == {"type": "heading", "level": 1, "text": "Main Title"}
    assert blocks[1]["type"] == "paragraph"
    assert blocks[2] == {"type": "heading", "level": 2, "text": "Section 1"}
    assert blocks[3]["type"] == "list"
    assert blocks[3]["list_type"] == "bullet"
    assert blocks[4] == {"type": "heading", "level": 2, "text": "Section 2"}
    assert blocks[5]["type"] == "list"
    assert blocks[5]["list_type"] == "number"
    assert blocks[6]["type"] == "table"


def test_parse_inline_bold() -> None:
    """Test parsing bold text."""
    text = "This is **bold** text"
    runs = parse_inline_formatting(text)

    assert len(runs) == 3
    assert runs[0] == {"text": "This is "}
    assert runs[1] == {"text": "bold", "bold": True}
    assert runs[2] == {"text": " text"}


def test_parse_inline_italic() -> None:
    """Test parsing italic text."""
    text = "This is *italic* text"
    runs = parse_inline_formatting(text)

    assert len(runs) == 3
    assert runs[0] == {"text": "This is "}
    assert runs[1] == {"text": "italic", "italic": True}
    assert runs[2] == {"text": " text"}


def test_parse_inline_bold_italic() -> None:
    """Test parsing bold italic text."""
    text = "This is ***bold italic*** text"
    runs = parse_inline_formatting(text)

    assert len(runs) == 3
    assert runs[0] == {"text": "This is "}
    assert runs[1] == {"text": "bold italic", "bold": True, "italic": True}
    assert runs[2] == {"text": " text"}


def test_parse_inline_multiple_formats() -> None:
    """Test parsing multiple inline formats."""
    text = "**Bold** and *italic* and ***both***"
    runs = parse_inline_formatting(text)

    assert runs[0] == {"text": "Bold", "bold": True}
    assert runs[1] == {"text": " and "}
    assert runs[2] == {"text": "italic", "italic": True}
    assert runs[3] == {"text": " and "}
    assert runs[4] == {"text": "both", "bold": True, "italic": True}


def test_parse_empty_markdown() -> None:
    """Test parsing empty markdown."""
    markdown = ""
    blocks = parse_markdown(markdown)
    assert len(blocks) == 0


def test_parse_markdown_with_empty_lines() -> None:
    """Test that empty lines are skipped."""
    markdown = "# Title\n\n\nParagraph\n\n"
    blocks = parse_markdown(markdown)

    assert len(blocks) == 2
    assert blocks[0] == {"type": "heading", "level": 1, "text": "Title"}
    assert blocks[1] == {"type": "paragraph", "text": "Paragraph"}


def test_parse_list_with_formatting() -> None:
    """Test parsing lists with inline formatting."""
    markdown = "- **Bold item**\n- *Italic item*\n- Normal item"
    blocks = parse_markdown(markdown)

    assert len(blocks) == 1
    assert blocks[0]["items"] == ["**Bold item**", "*Italic item*", "Normal item"]
