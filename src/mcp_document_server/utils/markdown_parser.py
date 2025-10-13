"""Parse markdown content for document generation."""

import re
from typing import Any


def parse_markdown(markdown: str) -> list[dict[str, Any]]:
    """
    Parse markdown content into structured format for document generation.

    Supports:
    - Headings (H1-H6): # to ######
    - Paragraphs with formatting: **bold**, *italic*, __underline__
    - Bulleted lists: -, *, +
    - Numbered lists: 1., 2., etc.
    - Tables: | col1 | col2 |

    Args:
        markdown: Markdown string to parse

    Returns:
        List of content blocks with type and properties
    """
    blocks: list[dict[str, Any]] = []
    lines = markdown.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            i += 1
            continue

        # Parse headings
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2)
            blocks.append({"type": "heading", "level": level, "text": text})
            i += 1
            continue

        # Parse tables
        if "|" in stripped and i + 1 < len(lines) and "|" in lines[i + 1]:
            table_data = _parse_table(lines, i)
            if table_data:
                blocks.append(table_data["block"])
                i = table_data["next_index"]
                continue

        # Parse bulleted lists
        if re.match(r"^[-*+]\s+", stripped):
            list_data = _parse_list(lines, i, "bullet")
            blocks.append(list_data["block"])
            i = list_data["next_index"]
            continue

        # Parse numbered lists
        if re.match(r"^\d+\.\s+", stripped):
            list_data = _parse_list(lines, i, "number")
            blocks.append(list_data["block"])
            i = list_data["next_index"]
            continue

        # Default: paragraph
        blocks.append({"type": "paragraph", "text": stripped})
        i += 1

    return blocks


def _parse_table(lines: list[str], start_index: int) -> dict[str, Any] | None:
    """
    Parse a markdown table starting at the given index.

    Args:
        lines: All lines in the document
        start_index: Index of the first table line

    Returns:
        Dictionary with block data and next_index, or None if not a valid table
    """
    rows: list[list[str]] = []
    i = start_index

    while i < len(lines):
        line = lines[i].strip()
        if not line or "|" not in line:
            break

        # Skip separator line (e.g., |---|---|)
        if re.match(r"^\|[\s\-:|]+\|$", line):
            i += 1
            continue

        # Parse table row
        cells = [cell.strip() for cell in line.split("|")[1:-1]]
        rows.append(cells)
        i += 1

    if len(rows) < 2:  # Need at least header + one data row
        return None

    return {
        "block": {
            "type": "table",
            "headers": rows[0],
            "rows": rows[1:],
        },
        "next_index": i,
    }


def _parse_list(lines: list[str], start_index: int, list_type: str) -> dict[str, Any]:
    """
    Parse a markdown list starting at the given index.

    Args:
        lines: All lines in the document
        start_index: Index of the first list item
        list_type: Either 'bullet' or 'number'

    Returns:
        Dictionary with block data and next_index
    """
    items: list[str] = []
    i = start_index
    pattern = r"^[-*+]\s+" if list_type == "bullet" else r"^\d+\.\s+"

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        match = re.match(pattern, line)
        if not match:
            break

        # Extract item text (remove list marker)
        item_text = re.sub(pattern, "", line).strip()
        items.append(item_text)
        i += 1

    return {
        "block": {
            "type": "list",
            "list_type": list_type,
            "items": items,
        },
        "next_index": i,
    }


def parse_inline_formatting(text: str) -> list[dict[str, Any]]:
    """
    Parse inline formatting within text (bold, italic, underline).

    Supports:
    - **bold** or __bold__
    - *italic* or _italic_
    - ***bold italic***

    Args:
        text: Text with inline markdown formatting

    Returns:
        List of text runs with formatting properties
    """
    runs: list[dict[str, Any]] = []

    # Simple regex-based approach for inline formatting
    # Pattern: matches ***text***, **text**, *text*, __text__, _text_
    pattern = r"(\*\*\*[^*]+\*\*\*|\*\*[^*]+\*\*|\*[^*]+\*|__[^_]+__|_[^_]+_|[^*_]+)"

    for match in re.finditer(pattern, text):
        segment = match.group(0)

        # Bold italic
        if segment.startswith("***") and segment.endswith("***"):
            runs.append(
                {
                    "text": segment[3:-3],
                    "bold": True,
                    "italic": True,
                }
            )
        # Bold
        elif (segment.startswith("**") and segment.endswith("**")) or (
            segment.startswith("__") and segment.endswith("__")
        ):
            runs.append(
                {
                    "text": segment[2:-2],
                    "bold": True,
                }
            )
        # Italic
        elif (segment.startswith("*") and segment.endswith("*")) or (
            segment.startswith("_") and segment.endswith("_")
        ):
            runs.append(
                {
                    "text": segment[1:-1],
                    "italic": True,
                }
            )
        # Plain text
        else:
            runs.append(
                {
                    "text": segment,
                }
            )

    return runs
