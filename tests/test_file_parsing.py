"""Tests for file parsing functions."""
import io
import pytest
from app import parse_txt, parse_xlsx, parse_pdf, parse_file, allowed_file, _is_audio_file


class TestAllowedFile:
    def test_xlsx_allowed(self):
        assert allowed_file("cut_sheet.xlsx") is True

    def test_pdf_allowed(self):
        assert allowed_file("notes.pdf") is True

    def test_txt_allowed(self):
        assert allowed_file("transcript.txt") is True

    def test_mp3_allowed(self):
        assert allowed_file("interview.mp3") is True

    def test_wav_allowed(self):
        assert allowed_file("recording.wav") is True

    def test_m4a_allowed(self):
        assert allowed_file("audio.m4a") is True

    def test_mp4_allowed(self):
        assert allowed_file("video.mp4") is True

    def test_exe_rejected(self):
        assert allowed_file("hack.exe") is False

    def test_no_extension_rejected(self):
        assert allowed_file("noext") is False

    def test_empty_string_rejected(self):
        assert allowed_file("") is False

    def test_docx_rejected(self):
        assert allowed_file("document.docx") is False


class TestIsAudioFile:
    def test_mp3_is_audio(self):
        assert _is_audio_file("interview.mp3") is True

    def test_wav_is_audio(self):
        assert _is_audio_file("recording.wav") is True

    def test_m4a_is_audio(self):
        assert _is_audio_file("audio.m4a") is True

    def test_flac_is_audio(self):
        assert _is_audio_file("lossless.flac") is True

    def test_mp4_is_audio(self):
        assert _is_audio_file("video.mp4") is True

    def test_txt_not_audio(self):
        assert _is_audio_file("notes.txt") is False

    def test_xlsx_not_audio(self):
        assert _is_audio_file("sheet.xlsx") is False

    def test_pdf_not_audio(self):
        assert _is_audio_file("doc.pdf") is False

    def test_none_not_audio(self):
        assert _is_audio_file(None) is False

    def test_no_extension_not_audio(self):
        assert _is_audio_file("noext") is False


class TestParseTxt:
    def test_basic_parse(self):
        result = parse_txt(b"Hello world\nLine 2")
        assert "Hello world" in result
        assert "Line 2" in result

    def test_utf8_content(self):
        result = parse_txt("Héllo wörld".encode("utf-8"))
        assert "Héllo" in result

    def test_empty_file(self):
        result = parse_txt(b"")
        assert result == ""


class TestParseXlsx:
    def test_basic_xlsx(self, sample_xlsx_bytes):
        result = parse_xlsx(sample_xlsx_bytes)
        assert "Cut Sheet" in result
        assert "Introduction" in result
        assert "Timestamp" in result

    def test_multi_row(self, sample_xlsx_bytes):
        result = parse_xlsx(sample_xlsx_bytes)
        assert "childhood" in result


class TestParseFile:
    def test_txt_dispatch(self):
        result = parse_file(b"Hello test content", "notes.txt")
        assert "Hello test content" in result

    def test_xlsx_dispatch(self, sample_xlsx_bytes):
        result = parse_file(sample_xlsx_bytes, "sheet.xlsx")
        assert "Introduction" in result

    def test_unsupported_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            parse_file(b"data", "file.docx")
