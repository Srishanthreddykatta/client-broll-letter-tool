"""Tests for client brief document formatting."""
import os

import pytest
from brief_document import (
    sanitize_brief_markdown,
    sanitize_brief_markdown_v2,
    remove_visual_reference_section,
    style_brief_html_tables,
    md_to_brief_fragment,
    _ensure_section_a_table,
    _ensure_section_a_v2_table,
    _ensure_photo_context_table,
    _ensure_video_shots_table,
    _ensure_closing_paragraph,
    _ensure_client_front_matter,
    _generalize_ages_in_text,
    _build_page_break_plan,
    _needs_page_break_before_next,
    build_production_brief,
    build_client_brief_html,
    PAGE_TOP_MAX_ROWS,
    ROWS_PER_PAGE,
)


SAMPLE_WITH_IMAGES = """## SECTION: VISUAL REFERENCE IMAGES

**Shot 1 — Test**

[REFERENCE IMAGE: Shot 1 — Test]

## SECTION: VIDEOGRAPHER TECHNICAL REQUIREMENTS

| **Format** | **Lighting** |
|---|---|
| 4K | Natural |
"""

SAMPLE_SECTION_A_LINES = """## SECTION A — PHOTOS

**CHILDHOOD**

1. Photo around age 6 - School or city image

## SECTION B — VIDEO
"""

SAMPLE_PHOTO_CONTEXT = """## SECTION: PHOTO CONTEXT — WHY WE NEED THESE

**CHILDHOOD**

**1. Photo of you around age 6 —**

*"She said this."* This sets your origin story.

## SECTION: VIDEO SHOT DETAILS — THE WHY BEHIND EACH SHOT

**Story Shots (12–19) | These appear at specific moments in your episode**

| **Shot 12 · Morning Ritual** *20–30 sec* | **Before:** *"My name is Rachel."* **Mood:** Purposeful energy. |

## SECTION: VIDEOGRAPHER TECHNICAL REQUIREMENTS
"""


class TestSanitizeBrief:
    def test_removes_visual_reference_section(self):
        result = sanitize_brief_markdown(SAMPLE_WITH_IMAGES)
        assert "VISUAL REFERENCE" not in result
        assert "REFERENCE IMAGE" not in result
        assert "VIDEOGRAPHER" in result

    def test_strips_checkmarks_and_prefixes(self):
        md = "| 1 | test | ✓ Quick: At home | ◎ Better: At office |"
        result = sanitize_brief_markdown(md)
        assert "✓" not in result
        assert "Quick:" not in result
        assert "At home" in result

    def test_strips_format_hint(self):
        md = "## SECTION A\n\n_Format: [What to find]_\n\n**CHILDHOOD**\n"
        result = sanitize_brief_markdown(md)
        assert "_Format:" not in result


class TestSectionATable:
    def test_converts_dash_lines_to_table(self):
        result = _ensure_section_a_table(SAMPLE_SECTION_A_LINES)
        assert "| **#** | **What to find** |" in result
        assert "| 1 | Photo around age 6 |" in result
        assert "| **CHILDHOOD** | | |" in result

    def test_converts_schema_lines_to_table(self):
        md = """## SECTION A — PHOTOS

[Item] [A little more detail] [alternative] [alternative detail]

**CHILDHOOD**

Photo of you around age 6 - Ideally around age 6 - Photos that represent your childhood (ex. Neighbourhood, city, or school image)

## SECTION B — VIDEO
"""
        result = _ensure_section_a_table(md)
        assert "[Item]" not in result
        assert "| 1 | Photo of you around age 6 | Neighbourhood" in result


class TestSectionAV2Table:
    def test_converts_v1_table_to_v2_columns(self):
        md = """## SECTION A — PHOTOS

| **#** | **What to find** | **Don't have it? Use this instead** |
|---|---|---|
| **CHILDHOOD** | | |
| 1 | Photo of you around age 6 | Neighbourhood, city, or school image |

## SECTION B — VIDEO
"""
        result = _ensure_section_a_v2_table(md)
        assert "**Photo**" in result
        assert "**A little more detail**" in result
        assert "**Good to have**" in result
        assert "**Alternative option**" in result
        assert "Examples" not in result.split("SECTION B")[0]
        assert "Childhood photo" in result
        assert "early childhood (roughly ages 4–8)" in result
        assert "Photos that represent your childhood" in result
        assert "Neighbourhood" in result

    def test_sanitize_v2(self):
        md = """## SECTION A — PHOTOS
| **#** | **What to find** | **Don't have it? Use this instead** |
|---|---|---|
| 1 | Photo of you around age 6 | School, city |
## SECTION B
"""
        result = sanitize_brief_markdown_v2(md)
        assert "**Good to have**" in result


class TestPhotoContextTable:
    def test_converts_prose_to_table(self):
        result = _ensure_photo_context_table(SAMPLE_PHOTO_CONTEXT)
        assert "| **#** | **Photo** | **Episode quote** |" in result
        assert '| 1 | Photo of you around age 6 |' in result
        assert "She said this" in result


class TestVideoShotsTable:
    def test_merges_shot_rows(self):
        result = _ensure_video_shots_table(SAMPLE_PHOTO_CONTEXT)
        assert "| **Shot · Duration** | **Before (from episode)** |" in result
        assert "Shot 12" in result
        assert "My name is Rachel" in result


class TestTableStyling:
    def test_header_cells_get_black_background(self):
        html = "<table><tr><th>#</th><th>What</th></tr><tr><td>1</td><td>Item</td></tr></table>"
        styled = style_brief_html_tables(html)
        assert "#000000" in styled
        assert "brief-table" in styled

    def test_category_row_styled(self):
        html = "<table><tr><td><strong>CHILDHOOD</strong></td><td></td></tr></table>"
        styled = style_brief_html_tables(html)
        assert "#000000" in styled
        assert "#FFFFFF" in styled
        assert 'color:#FFFFFF' in styled

    def test_instruction_box_rows_black(self):
        html = (
            "<table><tr><th>MUST READ</th></tr>"
            "<tr><td>Upload via Google Drive</td></tr></table>"
        )
        styled = style_brief_html_tables(html)
        assert styled.count("#000000") >= 2
        assert "#FFFFFF" in styled


class TestMdToBriefFragment:
    def test_renders_markdown(self):
        html = md_to_brief_fragment("## Hello\n\nParagraph.")
        assert "<h2>" in html
        assert "Paragraph" in html

    def test_detailed_context_always_page_breaks(self):
        md = "# DETAILED CONTEXT & VIDEOGRAPHER NOTES\n\n*Share this page.*\n"
        html = md_to_brief_fragment(md)
        assert "mso-page-break-before:always" in html
        assert html.index("page-break") < html.index("DETAILED CONTEXT")

    def test_closing_has_no_pipe_wrappers(self):
        md = """## SECTION: CLOSING

| *Hello* world. **— Team** |
"""
        html = md_to_brief_fragment(_ensure_closing_paragraph(md))
        assert "brief-closing" in html
        assert "#f5f0e6" in html
        assert "<p>|" not in html


class TestPageBreakPlan:
    def test_break_when_previous_section_ends_low_on_page(self):
        assert _needs_page_break_before_next(ROWS_PER_PAGE + PAGE_TOP_MAX_ROWS + 1)
        assert not _needs_page_break_before_next(
            ROWS_PER_PAGE + PAGE_TOP_MAX_ROWS, min_rows_needed=2
        )

    def test_break_when_page_one_has_no_room(self):
        assert _needs_page_break_before_next(ROWS_PER_PAGE - 2, min_rows_needed=10)

    def test_nilu_brief_layout_plan(self):
        path = os.path.join(
            os.path.dirname(__file__),
            "fixtures",
            "nilu_naderi_brief_v2.md",
        )
        if not os.path.isfile(path):
            pytest.skip("Nilu sample markdown not found")
        with open(path, encoding="utf-8") as f:
            md = sanitize_brief_markdown_v2(f.read())
        plan = _build_page_break_plan(md)
        assert plan["detailed_context"]
        assert plan["section_b"]
        assert plan["section_c"]
        # Section D (interviews) may need a break when archival + footage fill the page.
        assert "section_d" in plan
        assert not plan["photo_context"]


    def test_checklist_migrates_section_b_archival(self):
        md = """# QUICK CHECKLIST

## SECTION A — PHOTOS & ARCHIVAL (2 items)

| **Photo** | **A little more detail** | **Good to have** | **Alternative option** |
|---|---|---|---|
| **CHILDHOOD** | | | |
| Childhood photo | Early years | Childhood photos | School image |

---

## SECTION B — NEW VIDEO FOOTAGE (2 shots)

| **#** | **Shot** | **Quick** | **Pro** |
|---|---|---|---|
| 1 | **Test** | Home | Office |

---

## SECTION C — INTERVIEW CLIPS (1 people)

| **Interview 1** |
|---|
| Test |

---
# DETAILED CONTEXT
"""
        out = sanitize_brief_markdown_v2(md)
        assert "SECTION B — VIDEOS & ARCHIVAL" in out
        assert "Childhood home video" in out
        assert "SECTION C — NEW VIDEO FOOTAGE" in out
        assert "SECTION D — INTERVIEW" in out

    def test_build_production_brief_no_generated_date(self):
        md = "# QUICK CHECKLIST\n\n## SECTION A — PHOTOS\n"
        clean, html = build_production_brief(md, "Test Client", "Test Episode")
        assert "Generated" not in html
        assert "Test Client" in html
        assert "INSTRUCTIONS FOR THE CLIENT" in clean
        assert "Your upload folder tree" in clean
        assert "Section E — Extras" in clean
        must_read_block = clean.split("Your upload folder tree")[0]
        assert "Section E — Extras" in must_read_block
        assert must_read_block.index("File naming") < must_read_block.index("Section E — Extras")
        assert "**A | PHOTOS" not in clean
        assert "childhood_photo_1" in clean
        assert "SECTION D" not in clean or "SECTION D — INTERVIEW" in clean
        assert "**Photo**" in clean or "SECTION A" in clean

    def test_client_front_matter_injected_in_html(self):
        md = "# QUICK CHECKLIST\n\n## SECTION A — PHOTOS\n"
        html = build_client_brief_html(md, "Test Client", "Test Episode")
        assert "INSTRUCTIONS FOR THE CLIENT" in html
        assert "Section C — New Video Footage" in html
        assert "Section E — Extras" in html
        assert "How to submit" in html
        assert "doc-logo" in html

    def test_generalize_specific_ages(self):
        text = "You around age 6 and at age 31 in the photo"
        out = _generalize_ages_in_text(text)
        assert "age 6" not in out
        assert "age 31" not in out
        assert "early childhood" in out
        assert "thirties" in out


class TestClosingParagraph:
    def test_strips_pipe_table(self):
        md = "## SECTION: CLOSING\n\n| *Hi* there. **— Team** |\n"
        out = _ensure_closing_paragraph(md)
        assert "| *Hi*" not in out
        assert "*Hi* there" in out
