"""Tests for B-roll reference image generation and matching."""
import pytest
from app import (
    build_image_prompt,
    build_reference_image_html,
    compress_reference_image,
    _find_matching_image,
    safe_client_filename,
    REFERENCE_IMAGE_MAX_WIDTH,
)


class TestBuildImagePrompt:
    def test_includes_scene(self):
        prompt = build_image_prompt("Morning Walk", "Context about morning")
        assert "Morning Walk" in prompt
        assert "cinematic" in prompt.lower()

    def test_lifestyle_pool_hint(self):
        prompt = build_image_prompt("Walking shot", "Pool context", lifestyle_pool=True)
        assert "Lifestyle Pool" in prompt

    def test_transcript_hint_added(self):
        prompt = build_image_prompt("Scene", "You just said: 'I started at dawn'")
        assert "emotional tone" in prompt.lower()


class TestBuildReferenceImageHtml:
    def test_contains_img_tag(self):
        img = {"header": "Test Shot", "b64": "abc123", "mime": "image/png", "width": 300}
        html = build_reference_image_html(img, "Test Shot")
        assert '<img' in html
        assert 'abc123' in html
        assert 'broll-reference-still' in html

    def test_custom_title(self):
        img = {"header": "Original", "b64": "x", "mime": "image/jpeg", "width": 300}
        html = build_reference_image_html(img, "Custom Title")
        assert "Custom Title" in html

    def test_default_width(self):
        img = {"header": "Shot", "b64": "data", "mime": "image/png"}
        html = build_reference_image_html(img)
        assert str(REFERENCE_IMAGE_MAX_WIDTH) in html


class TestCompressReferenceImage:
    def test_returns_tuple(self):
        import base64
        from PIL import Image
        import io

        img = Image.new("RGB", (800, 600), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()

        result_b64, result_mime = compress_reference_image(b64, "image/png")
        assert isinstance(result_b64, str)
        assert result_mime == "image/jpeg"
        assert len(result_b64) < len(b64)

    def test_small_image_not_upscaled(self):
        import base64
        from PIL import Image
        import io

        img = Image.new("RGB", (100, 80), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()

        result_b64, _ = compress_reference_image(b64, "image/png")
        assert isinstance(result_b64, str)


class TestFindMatchingImage:
    def test_exact_match(self):
        lookup = {"morning walk": {"header": "Morning Walk", "b64": "x"}}
        result = _find_matching_image("Morning Walk", lookup)
        assert result is not None
        assert result["header"] == "Morning Walk"

    def test_fuzzy_match(self):
        lookup = {"morning workspace": {"header": "Morning Workspace", "b64": "x"}}
        result = _find_matching_image("Morning workspace quiet focus", lookup)
        assert result is not None

    def test_no_match(self):
        lookup = {"ocean sunset": {"header": "Ocean Sunset", "b64": "x"}}
        result = _find_matching_image("Morning Walk", lookup)
        assert result is None


class TestSafeClientFilename:
    def test_basic_name(self):
        result = safe_client_filename("Marcus Williams", "Post-Edit_B-Roll_Brief", "pdf")
        assert result == "Marcus_Williams_Post-Edit_B-Roll_Brief.pdf"

    def test_special_chars_stripped(self):
        result = safe_client_filename("O'Brien & Co.", "Brief", "pdf")
        assert "&" not in result
        assert "'" not in result
        assert result.endswith(".pdf")

    def test_empty_name_fallback(self):
        result = safe_client_filename("", "Brief", "html")
        assert result.startswith("Client")
