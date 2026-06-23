"""
Post-process B-Roll brief .docx with Microsoft Word COM.
Applies page breaks from layout plan, section heading colors, and closing box styling.
"""

from __future__ import annotations

import re
from pathlib import Path

from brief_document import LOGO_DOCX_MAX_WIDTH_PT, _build_page_break_plan

# Word uses BGR for RGB()
def _rgb(r: int, g: int, b: int) -> int:
    return r + (g << 8) + (b << 16)


COLOR_SECTION = _rgb(0x8A, 0x72, 0x34)
COLOR_DETAILED = _rgb(0xC8, 0xA8, 0x4E)
COLOR_CLOSING_BG = _rgb(0xE6, 0xF0, 0xF5)  # #f5f0e6
COLOR_CLOSING_BORDER = _rgb(0x4E, 0xA8, 0xC8)  # #c8a84e
COLOR_CLOSING_TEXT = _rgb(0x1A, 0x1A, 0x1A)

SECTION_HEADING_RULES: list[tuple[str, str]] = [
    ("quick_checklist", r"^QUICK\s+CHECKLIST\b"),
    ("section_b", r"^SECTION\s+B\s*[—–-]\s*VIDEOS?\s*&\s*ARCHIVAL"),
    ("section_c", r"^SECTION\s+C\s*[—–-]\s*NEW\s+VIDEO"),
    ("section_d", r"^SECTION\s+D\s*[—–-]\s*INTERVIEW"),
    ("detailed_context", r"^DETAILED\s+CONTEXT\b"),
    ("photo_context", r"^SECTION:\s*PHOTO\s+CONTEXT\b"),
    ("video_shots", r"^SECTION:\s*VIDEO\s+SHOT\b"),
    ("videographer", r"^SECTION:\s*VIDEOGRAPHER\b"),
]


def _para_in_table(para) -> bool:
    try:
        return bool(para.Range.Information(12))  # wdWithInTable
    except Exception:
        return False


def _para_text(para) -> str:
    return (para.Range.Text or "").replace("\r", "").replace("\x07", "").strip()


def _resize_header_logo(doc, max_width_pt: float = LOGO_DOCX_MAX_WIDTH_PT) -> None:
    """Set header logo to a small but readable size (Word ignores HTML/CSS sizing)."""
    wd_inline_shape_picture = 3
    for para_idx in range(1, min(14, doc.Paragraphs.Count + 1)):
        shapes = doc.Paragraphs(para_idx).Range.InlineShapes
        for i in range(1, shapes.Count + 1):
            shape = shapes(i)
            try:
                if shape.Type != wd_inline_shape_picture:
                    continue
                width = float(shape.Width)
                if width <= 0:
                    continue
                shape.LockAspectRatio = -1
                ratio = float(shape.Height) / width
                shape.Width = max_width_pt
                shape.Height = max_width_pt * ratio
            except Exception:
                continue


def _compact_front_matter_page(doc) -> None:
    """Tighten spacing before QUICK CHECKLIST so page 1 fits instructions + folders + submit."""
    for i in range(1, doc.Paragraphs.Count + 1):
        para = doc.Paragraphs(i)
        text = _para_text(para)
        if re.search(r"^QUICK\s+CHECKLIST\b", text, re.IGNORECASE):
            para.Format.PageBreakBefore = -1
            break
        if _para_in_table(para):
            continue
        try:
            para.Format.SpaceBefore = 0
            para.Format.SpaceAfter = 0
            para.Format.LineSpacing = 12
            if "INSTRUCTIONS FOR THE CLIENT" in text.upper():
                para.Range.Font.Size = 10
            if "POST-EDIT B-ROLL" in text.upper():
                para.Range.Font.Size = 10
        except Exception:
            pass
    for t_idx in range(1, doc.Tables.Count + 1):
        table = doc.Tables(t_idx)
        try:
            header = table.Cell(1, 1).Range.Text.upper()
        except Exception:
            continue
        if not any(
            k in header
            for k in ("MUST READ", "FOLDER TREE", "HOW TO SUBMIT", "YOUR UPLOAD")
        ):
            continue
        try:
            table.Rows.HeightRule = 0
            for r in range(1, table.Rows.Count + 1):
                for c in range(1, table.Columns.Count + 1):
                    cell = table.Cell(r, c)
                    cell.Range.Font.Size = 8.5
                    cell.Range.Font.Name = "Arial"
        except Exception:
            pass


def apply_brief_formatting_to_doc(doc, brief_md: str | None = None) -> None:
    """Apply page breaks, heading colors, and closing box to an open Word document."""
    import time

    time.sleep(0.5)
    _resize_header_logo(doc)
    _compact_front_matter_page(doc)
    plan = _build_page_break_plan(brief_md or "") if brief_md else {}
    plan["detailed_context"] = True

    _remove_break_artifacts(doc)

    closing_heading_idx = None
    for i in range(1, doc.Paragraphs.Count + 1):
        para = doc.Paragraphs(i)
        text = _para_text(para)
        if not text:
            continue
        if _para_in_table(para):
            continue

        for plan_key, pattern in SECTION_HEADING_RULES:
            if re.search(pattern, text, re.IGNORECASE):
                if plan_key == "quick_checklist":
                    want_break = True
                elif plan_key == "section_d":
                    want_break = bool(plan.get(plan_key, False))
                else:
                    want_break = bool(
                        plan.get(plan_key, plan_key == "detailed_context")
                    )
                para.Format.PageBreakBefore = -1 if want_break else 0
                if plan_key == "section_b" and not want_break:
                    para.Format.KeepWithNext = -1
                para.Range.Font.Name = "Arial"
                para.Range.Font.Bold = True
                if plan_key == "detailed_context":
                    para.Range.Font.Size = 13
                    para.Range.Font.Color = COLOR_DETAILED
                else:
                    para.Range.Font.Size = 10.5
                    para.Range.Font.Color = COLOR_SECTION
                para.Format.SpaceBefore = 6 if want_break else 3
                para.Format.SpaceAfter = 3
                break

        if re.search(r"^SECTION:\s*CLOSING\b", text, re.IGNORECASE):
            closing_heading_idx = i
            para.Range.Font.Name = "Arial"
            para.Range.Font.Bold = True
            para.Range.Font.Size = 10.5
            para.Range.Font.Color = COLOR_SECTION
            para.Format.PageBreakBefore = 0

    if closing_heading_idx:
        _style_closing_body(doc, closing_heading_idx)

    _keep_section_tables_with_headings(doc)


def _keep_section_tables_with_headings(doc) -> None:
    """Keep section heading on the same page as the table that follows (esp. Section B)."""
    section_patterns = (
        r"^SECTION\s+B\s*[—–-]\s*VIDEOS?\s*&\s*ARCHIVAL",
        r"^SECTION\s+C\s*[—–-]\s*NEW\s+VIDEO",
        r"^SECTION\s+D\s*[—–-]\s*INTERVIEW",
    )
    for i in range(1, doc.Paragraphs.Count):
        para = doc.Paragraphs(i)
        if _para_in_table(para):
            continue
        text = _para_text(para)
        if not any(re.search(p, text, re.IGNORECASE) for p in section_patterns):
            continue
        para.Format.KeepWithNext = -1
        rng = para.Range
        if rng.Tables.Count > 0:
            tbl = rng.Tables(1)
            try:
                tbl.Rows.AllowBreakAcrossPages = 0
            except Exception:
                pass
        else:
            nxt = i + 1
            while nxt <= doc.Paragraphs.Count:
                npara = doc.Paragraphs(nxt)
                if npara.Range.Tables.Count > 0:
                    try:
                        npara.Range.Tables(1).Rows.AllowBreakAcrossPages = 0
                    except Exception:
                        pass
                    break
                if _para_text(npara) and re.search(
                    r"^SECTION\s+[A-D]\b", _para_text(npara), re.IGNORECASE
                ):
                    break
                nxt += 1


def _remove_break_artifacts(doc) -> None:
    """Delete 1pt spacer paragraphs left from HTML page-break hacks."""
    import time

    to_delete = []
    count = None
    for _ in range(8):
        try:
            count = doc.Paragraphs.Count
            break
        except Exception:
            time.sleep(0.5)
    if not count:
        return
    for i in range(1, count + 1):
        para = doc.Paragraphs(i)
        text = _para_text(para)
        if text in ("", "\u00a0", " "):
            size = para.Range.Font.Size
            if size and size <= 2:
                to_delete.append(i)
    for i in reversed(to_delete):
        doc.Paragraphs(i).Range.Delete()


def postprocess_brief_docx(docx_path: Path, brief_md: str | None = None) -> bool:
    """Re-open saved .docx and apply formatting (used when not converting in-process)."""
    try:
        import win32com.client
    except ImportError:
        return False

    docx_path = docx_path.resolve()
    if not docx_path.is_file():
        return False

    word = win32com.client.Dispatch("Word.Application")
    _word_quiet(word)
    doc = None
    try:
        doc = word.Documents.Open(str(docx_path))
        apply_brief_formatting_to_doc(doc, brief_md)
        doc.Save()
        return True
    finally:
        if doc is not None:
            doc.Close(False)
        word.Quit()


def _word_quiet(word) -> None:
    try:
        word.Visible = False
    except Exception:
        pass
    try:
        word.DisplayAlerts = 0
    except Exception:
        pass


def _style_closing_body(doc, closing_heading_idx: int) -> None:
    """Shaded italic closing message — table cell or following paragraph(s)."""
    wdBorderLeft = 4
    styled = False
    for j in range(closing_heading_idx + 1, min(closing_heading_idx + 6, doc.Paragraphs.Count + 1)):
        para = doc.Paragraphs(j)
        text = _para_text(para)
        if not text:
            continue
        if re.search(r"^SECTION\b", text, re.IGNORECASE):
            break
        if "Production Team" in text or "you've shared" in text.lower() or styled:
            rng = para.Range
            rng.Font.Name = "Arial"
            rng.Font.Size = 10
            rng.Font.Italic = -1
            rng.Font.Color = COLOR_CLOSING_TEXT
            rng.ParagraphFormat.Shading.BackgroundPatternColor = COLOR_CLOSING_BG
            rng.ParagraphFormat.LeftIndent = 14
            rng.ParagraphFormat.RightIndent = 0
            rng.ParagraphFormat.SpaceBefore = 4
            rng.ParagraphFormat.SpaceAfter = 4
            border = rng.Borders(wdBorderLeft)
            border.LineStyle = 1
            border.Color = COLOR_CLOSING_BORDER
            border.LineWidth = 6
            styled = True
            break

    if styled:
        return

    for t_idx in range(1, doc.Tables.Count + 1):
        table = doc.Tables(t_idx)
        try:
            cell_text = table.Cell(1, 1).Range.Text
        except Exception:
            continue
        if "Production Team" in cell_text or "you've shared" in cell_text.lower():
            cell = table.Cell(1, 1)
            cell.Shading.BackgroundPatternColor = COLOR_CLOSING_BG
            cell.Range.Font.Name = "Arial"
            cell.Range.Font.Size = 10
            cell.Range.Font.Italic = -1
            cell.Range.Font.Color = COLOR_CLOSING_TEXT
            border = cell.Borders(wdBorderLeft)
            border.LineStyle = 1
            border.Color = COLOR_CLOSING_BORDER
            border.LineWidth = 6
            break
