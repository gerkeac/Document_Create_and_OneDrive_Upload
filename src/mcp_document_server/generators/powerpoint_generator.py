"""PowerPoint presentation generation using python-pptx."""

import logging
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.util import Inches, Pt

logger = logging.getLogger(__name__)


class PowerPointGenerator:
    """Generate PowerPoint presentations from structured content."""

    def __init__(self) -> None:
        """Initialize the PowerPoint generator."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def generate_presentation(
        self, slides: list[dict[str, Any]], output_path: Path, theme: str = "default"
    ) -> Path:
        """
        Generate a PowerPoint presentation from slide data.

        Args:
            slides: List of slide dictionaries with layout, title, content
            output_path: Path where the presentation should be saved
            theme: Theme name (default, blue, professional, minimal)

        Returns:
            Path to the generated presentation

        Raises:
            ValueError: If slide data is invalid
        """
        try:
            self.logger.info(
                f"Generating PowerPoint presentation with {len(slides)} slides, theme={theme}"
            )

            # Create presentation
            prs = Presentation()
            prs.slide_width = Inches(10)
            prs.slide_height = Inches(7.5)

            # Process each slide
            for idx, slide_data in enumerate(slides):
                self._add_slide(prs, slide_data, idx)

            # Save presentation
            output_path.parent.mkdir(parents=True, exist_ok=True)
            prs.save(str(output_path))

            self.logger.info(f"PowerPoint presentation saved to {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Error generating PowerPoint: {e}", exc_info=True)
            raise

    def _add_slide(self, prs: Presentation, slide_data: dict[str, Any], idx: int) -> None:
        """Add a slide to the presentation based on layout type."""
        layout_type = slide_data.get("layout", "title_content")

        self.logger.debug(f"Adding slide {idx + 1} with layout '{layout_type}'")

        if layout_type == "title":
            self._add_title_slide(prs, slide_data)
        elif layout_type == "title_content":
            self._add_title_content_slide(prs, slide_data)
        elif layout_type == "title_two_columns":
            self._add_title_two_columns_slide(prs, slide_data)
        elif layout_type == "title_table":
            self._add_title_table_slide(prs, slide_data)
        elif layout_type == "blank":
            self._add_blank_slide(prs, slide_data)
        else:
            self.logger.warning(f"Unknown layout '{layout_type}', using title_content")
            self._add_title_content_slide(prs, slide_data)

    def _add_title_slide(self, prs: Presentation, slide_data: dict[str, Any]) -> None:
        """Add a title slide (layout 0)."""
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        title = slide.shapes.title
        subtitle = slide.placeholders[1]

        title.text = slide_data.get("title", "")
        subtitle.text = slide_data.get("subtitle", "")

    def _add_title_content_slide(self, prs: Presentation, slide_data: dict[str, Any]) -> None:
        """Add a title + content (bullets) slide (layout 1)."""
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        title = slide.shapes.title
        content = slide.placeholders[1]

        title.text = slide_data.get("title", "")

        # Add content
        text_frame = content.text_frame
        text_frame.clear()  # Clear default text

        content_items = slide_data.get("content", [])
        if isinstance(content_items, str):
            content_items = [content_items]

        for i, item in enumerate(content_items):
            if i == 0:
                p = text_frame.paragraphs[0]
            else:
                p = text_frame.add_paragraph()

            p.text = str(item)
            p.level = 0
            p.font.size = Pt(18)

            # Check for nested items (sub-bullets)
            if isinstance(item, dict):
                p.text = str(item.get("text", ""))
                sub_items = item.get("sub_items", [])
                for sub_item in sub_items:
                    p_sub = text_frame.add_paragraph()
                    p_sub.text = str(sub_item)
                    p_sub.level = 1
                    p_sub.font.size = Pt(16)

    def _add_title_two_columns_slide(self, prs: Presentation, slide_data: dict[str, Any]) -> None:
        """Add a title + two columns slide (using blank layout with shapes)."""
        slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout

        # Add title
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(0.8))
        title_frame = title_box.text_frame
        title_p = title_frame.paragraphs[0]
        title_p.text = slide_data.get("title", "")
        title_p.font.size = Pt(32)
        title_p.font.bold = True

        # Add left column
        left_content = slide_data.get("left_content", [])
        left_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(4.5), Inches(5.5))
        self._fill_textbox(left_box.text_frame, left_content)

        # Add right column
        right_content = slide_data.get("right_content", [])
        right_box = slide.shapes.add_textbox(Inches(5.0), Inches(1.5), Inches(4.5), Inches(5.5))
        self._fill_textbox(right_box.text_frame, right_content)

    def _add_title_table_slide(self, prs: Presentation, slide_data: dict[str, Any]) -> None:
        """Add a title + table slide."""
        slide = prs.slides.add_slide(prs.slide_layouts[5])  # Title only layout
        title = slide.shapes.title
        title.text = slide_data.get("title", "")

        # Get table data
        table_data = slide_data.get("table", {})
        headers = table_data.get("headers", [])
        rows_data = table_data.get("rows", [])

        if not headers and not rows_data:
            return

        # Create table
        num_cols = len(headers) if headers else len(rows_data[0]) if rows_data else 1
        num_rows = len(rows_data) + (1 if headers else 0)

        # Position table below title
        left = Inches(1.0)
        top = Inches(2.0)
        width = Inches(8.0)
        height = Inches(0.8) * num_rows

        table = slide.shapes.add_table(num_rows, num_cols, left, top, width, height).table

        # Add headers
        if headers:
            for col_idx, header in enumerate(headers):
                cell = table.cell(0, col_idx)
                cell.text = str(header)
                cell.text_frame.paragraphs[0].font.bold = True
                cell.text_frame.paragraphs[0].font.size = Pt(14)

        # Add data rows
        start_row = 1 if headers else 0
        for row_idx, row_data in enumerate(rows_data):
            for col_idx, cell_data in enumerate(row_data):
                cell = table.cell(start_row + row_idx, col_idx)
                cell.text = str(cell_data)
                cell.text_frame.paragraphs[0].font.size = Pt(12)

    def _add_blank_slide(self, prs: Presentation, slide_data: dict[str, Any]) -> None:
        """Add a blank slide with custom content."""
        slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout

        # Add title if provided
        if "title" in slide_data:
            title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(0.8))
            title_frame = title_box.text_frame
            title_p = title_frame.paragraphs[0]
            title_p.text = slide_data.get("title", "")
            title_p.font.size = Pt(32)
            title_p.font.bold = True

        # Add content if provided
        if "content" in slide_data:
            content_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(9), Inches(5.5))
            content_items = slide_data.get("content", [])
            if isinstance(content_items, str):
                content_items = [content_items]
            self._fill_textbox(content_box.text_frame, content_items)

    def _fill_textbox(self, text_frame: Any, content_items: list[Any]) -> None:
        """Fill a textbox with content items."""
        text_frame.clear()

        if isinstance(content_items, str):
            content_items = [content_items]

        for i, item in enumerate(content_items):
            if i == 0:
                p = text_frame.paragraphs[0]
            else:
                p = text_frame.add_paragraph()

            p.text = str(item)
            p.font.size = Pt(18)
