"""Tests for prompt construction and output formatting rules."""
import pytest
from app import build_prompt_text, build_editor_prompt_text, MASTER_PROMPT, md_to_html


class TestBuildPromptText:
    def test_includes_client_name(self):
        result = build_prompt_text("Marcus", "Marcus Williams", "Rise Up", "Tech", "May 30", "")
        assert "Marcus" in result
        assert "Marcus Williams" in result

    def test_includes_episode_title(self):
        result = build_prompt_text("Jane", "Jane Doe", "Breaking Through", "Finance", "", "")
        assert "Breaking Through" in result

    def test_deadline_tbd_when_empty(self):
        result = build_prompt_text("Test", "Test User", "EP1", "Health", "", "")
        assert "TBD" in result

    def test_editor_notes_included(self):
        result = build_prompt_text("A", "A B", "T", "I", "D", "Focus on childhood trauma")
        assert "Focus on childhood trauma" in result


class TestMasterPromptContent:
    def test_has_page_one_checklist(self):
        assert "QUICK CHECKLIST" in MASTER_PROMPT

    def test_has_client_instructions(self):
        assert "MUST READ" in MASTER_PROMPT
        assert "Your upload folder tree" in MASTER_PROMPT
        assert "SECTION B — VIDEOS & ARCHIVAL" in MASTER_PROMPT
        assert "Section E — Extras" in MASTER_PROMPT

    def test_has_age_range_rule(self):
        assert "AGE RANGE RULE" in MASTER_PROMPT
        assert "Never use a specific age" in MASTER_PROMPT

    def test_has_section_b_videos_archival(self):
        assert "SECTION B — VIDEOS & ARCHIVAL" in MASTER_PROMPT
        assert "**Video**" in MASTER_PROMPT

    def test_has_section_a_v2_columns(self):
        assert "**Photo**" in MASTER_PROMPT
        assert "**Alternative option**" in MASTER_PROMPT

    def test_has_section_c_new_footage(self):
        assert "SECTION C — NEW VIDEO FOOTAGE" in MASTER_PROMPT

    def test_has_location_consolidation_rule(self):
        assert "LOCATION CONSOLIDATION RULE" in MASTER_PROMPT

    def test_has_episode_quote_rule(self):
        assert "EPISODE QUOTE RULE" in MASTER_PROMPT

    def test_has_global_rules(self):
        assert "## GLOBAL RULES" in MASTER_PROMPT

    def test_has_page_two_videographer(self):
        assert "DETAILED CONTEXT & VIDEOGRAPHER NOTES" in MASTER_PROMPT

    def test_locations_consolidated(self):
        assert "no more than 3 locations" in MASTER_PROMPT
        assert "HOME / OFFICE" in MASTER_PROMPT

    def test_easy_tier_home_rule(self):
        assert "filmable at home or within walking distance" in MASTER_PROMPT

    def test_single_session_goal(self):
        assert "3-hour session" in MASTER_PROMPT

    def test_no_visual_reference_section(self):
        assert "Do NOT include a Visual Reference Images section" in MASTER_PROMPT


class TestEditorPromptText:
    def test_includes_subject(self):
        result = build_editor_prompt_text("Marcus Williams", "Rise Up", "Next Level CEO", "23 min", "James")
        assert "Marcus Williams" in result

    def test_includes_date(self):
        result = build_editor_prompt_text("Test", "EP1", "Show", "20 min", "Ed")
        assert "202" in result


class TestMdToHtml:
    def test_basic_heading(self):
        result = md_to_html("# Hello")
        assert "<h1>" in result

    def test_bold_text(self):
        result = md_to_html("**Bold text**")
        assert "<strong>" in result

    def test_list(self):
        result = md_to_html("- Item 1\n- Item 2")
        assert "<li>" in result

    def test_numbered_list(self):
        result = md_to_html("1. First\n2. Second")
        assert "<ol>" in result or "<li>" in result
