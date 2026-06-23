"""Tests for brief enrichment, image extraction, and section processing."""
import pytest
from app import (
    extract_video_shoot_title_from_line,
    extract_locations_for_images,
    _is_valid_shot_title,
    _heading_needs_page_break,
    _normalize_heading_text,
    _section3_starts,
    _section3_ends,
    build_enriched_brief_html,
    _wrap_collapsible_sections,
    _add_major_section_page_break_classes,
    md_to_html,
)


class TestShotTitleExtraction:
    def test_numbered_shot_label_bold(self):
        line = '14. Shot Label: **Morning workspace — quiet focus**'
        assert extract_video_shoot_title_from_line(line) == "Morning workspace — quiet focus"

    def test_plain_shot_label(self):
        line = 'Shot Label: **Walking with purpose — outdoor**'
        assert extract_video_shoot_title_from_line(line) == "Walking with purpose — outdoor"

    def test_numbered_bold(self):
        line = '3. **Reflective moment — looking out a window**'
        assert extract_video_shoot_title_from_line(line) is not None

    def test_invalid_title_too_short(self):
        line = 'Shot Label: **Hi**'
        assert extract_video_shoot_title_from_line(line) is None

    def test_invalid_section_header(self):
        line = 'Shot Label: **Story-Specific Shots**'
        assert extract_video_shoot_title_from_line(line) is None

    def test_numbered_walking_shot(self):
        line = '22. Walking shot — golden hour outdoors'
        result = extract_video_shoot_title_from_line(line)
        assert result is not None

    def test_non_shot_line_ignored(self):
        line = 'Duration: Aim for 15-30 seconds'
        assert extract_video_shoot_title_from_line(line) is None

    def test_context_line_ignored(self):
        line = 'Transcript context: "I grew up in Detroit"'
        assert extract_video_shoot_title_from_line(line) is None


class TestValidShotTitle:
    def test_valid_title(self):
        assert _is_valid_shot_title("Morning workspace — quiet focus") is True

    def test_too_short(self):
        assert _is_valid_shot_title("Hi") is False

    def test_contains_invalid_substring(self):
        assert _is_valid_shot_title("Story-Specific Shots for the client") is False

    def test_section_header(self):
        assert _is_valid_shot_title("What we need from you") is False


class TestLocationExtraction:
    def test_extracts_from_section3(self):
        md = """## WHAT WE NEED FROM YOU: NEW VIDEO FOOTAGE (LIFESTYLE B-ROLL)

### A. Story-Specific Shots

14. Shot Label: **Morning Ritual**
Duration: 15-30 seconds
Context: You just said: 'I start every morning at 5am'

15. Shot Label: **Office Walk**
Duration: 15-30 seconds
Context: You just said: 'I walk into the office like I own the place'

### B. General Lifestyle Pool

20. Shot Label: **Walking shot — golden hour**
Duration: 15-30 seconds

## WHAT WE NEED FROM YOU: INTERVIEW CLIPS
"""
        locations = extract_locations_for_images(md)
        headers = [loc["header"] for loc in locations]
        assert "Morning Ritual" in headers
        assert "Office Walk" in headers

    def test_stops_at_section4(self):
        md = """## WHAT WE NEED FROM YOU: NEW VIDEO FOOTAGE (LIFESTYLE B-ROLL)

Shot Label: **Morning Walk**
Duration: 10s

## WHAT WE NEED FROM YOU: INTERVIEW CLIPS

Shot Label: **Should Not Extract**
Duration: 10s
"""
        locations = extract_locations_for_images(md)
        headers = [loc["header"] for loc in locations]
        assert "Morning Walk" in headers
        assert "Should Not Extract" not in headers


class TestHeadingPageBreak:
    def test_photos_section_gets_break(self):
        assert _heading_needs_page_break("WHAT WE NEED FROM YOU: PHOTOS & ARCHIVAL FOOTAGE") is True

    def test_video_section_gets_break(self):
        assert _heading_needs_page_break("WHAT WE NEED FROM YOU: NEW VIDEO FOOTAGE") is True

    def test_opening_letter_no_break(self):
        assert _heading_needs_page_break("OPENING LETTER") is False

    def test_subcategory_no_break(self):
        assert _heading_needs_page_break("Childhood & Early Life") is False

    def test_lifestyle_pool_no_break(self):
        assert _heading_needs_page_break("General Lifestyle Pool") is False


class TestSection3Detection:
    def test_starts_with_keyword(self):
        assert _section3_starts("what we need from you: new video footage (lifestyle b-roll)") is True

    def test_plain_new_video(self):
        assert _section3_starts("new video footage") is True

    def test_photos_is_not_section3(self):
        assert _section3_starts("photos & archival footage") is False

    def test_section4_ends_section3(self):
        assert _section3_ends("section 4 — interview clips") is True

    def test_videographer_ends_section3(self):
        assert _section3_ends("videographer instructions") is True


class TestCollapsibleSections:
    def test_tldr_extracted(self):
        html = (
            '<h2>AT A GLANCE</h2><p>Summary here</p>'
            '<h2>Photos Section</h2><p>Photo details</p>'
            '<h2>Video Section</h2><p>Video details</p>'
        )
        result = _wrap_collapsible_sections(html)
        assert 'class="tldr-box"' in result
        assert '<details' in result
        assert 'brief-section' in result

    def test_no_tldr_returns_original(self):
        html = '<h2>Photos Section</h2><p>Details</p>'
        result = _wrap_collapsible_sections(html)
        assert result == html

    def test_sections_have_open_attribute(self):
        html = (
            '<h2>AT A GLANCE</h2><p>Quick summary</p>'
            '<h2>Section One</h2><p>Content 1</p>'
        )
        result = _wrap_collapsible_sections(html)
        assert 'open' in result


class TestBuildEnrichedHtml:
    def test_basic_markdown_converts(self):
        md = "# Title\n\nHello world\n"
        result = build_enriched_brief_html(md, [])
        assert "Hello world" in result
        assert "<" in result

    def test_transcript_label_class(self):
        md = "**From your episode:** quote here\n"
        result = build_enriched_brief_html(md, [])
        assert "transcript-label" in result
