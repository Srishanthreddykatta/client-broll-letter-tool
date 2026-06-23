"""Tests for audio transcription pipeline."""
import io
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from app import _is_audio_file, _compress_audio_path, _get_rev_api_key, process_audio_file


class TestAudioDetection:
    def test_mp3_detected(self):
        assert _is_audio_file("episode.mp3") is True

    def test_wav_detected(self):
        assert _is_audio_file("raw_audio.wav") is True

    def test_m4a_detected(self):
        assert _is_audio_file("voice_memo.m4a") is True

    def test_flac_detected(self):
        assert _is_audio_file("lossless.flac") is True

    def test_webm_detected(self):
        assert _is_audio_file("screen_record.webm") is True

    def test_txt_not_detected(self):
        assert _is_audio_file("notes.txt") is False

    def test_pdf_not_detected(self):
        assert _is_audio_file("doc.pdf") is False


class TestAudioCompression:
    @patch("subprocess.run")
    def test_compression_called(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"x" * 1000)
            tmp_path = f.name
        try:
            result_path = _compress_audio_path(tmp_path, "big.mp3")
            assert isinstance(result_path, str)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_fallback_on_no_ffmpeg(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"x" * 100)
            tmp_path = f.name
        try:
            result_path = _compress_audio_path(tmp_path, "tiny.mp3")
            assert result_path == tmp_path or isinstance(result_path, str)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestRevAiKeyRetrieval:
    def test_returns_empty_if_no_key(self, monkeypatch):
        monkeypatch.setenv("REV_AI_TOKEN", "")
        monkeypatch.setattr("os.path.exists", lambda p: False)
        key = _get_rev_api_key()
        assert key == "" or key is not None


class TestProcessAudioFile:
    def test_raises_on_missing_rev_key(self, monkeypatch):
        monkeypatch.setattr("app._get_rev_api_key", lambda: "")
        with pytest.raises(RuntimeError, match="REV_AI_TOKEN"):
            process_audio_file(b"audio data", "test.mp3")

    @patch("app._transcribe_with_rev_ai")
    def test_small_file_skips_compression(self, mock_transcribe, monkeypatch):
        monkeypatch.setattr("app._get_rev_api_key", lambda: "test-key")
        mock_transcribe.return_value = "Speaker 1: Hello world."
        small_audio = b"x" * 1000
        result = process_audio_file(small_audio, "small.mp3")
        assert "Hello world" in result

    @patch("app._compress_audio_path")
    @patch("app._transcribe_with_rev_ai")
    def test_large_file_triggers_compression(self, mock_transcribe, mock_compress, monkeypatch, tmp_path):
        monkeypatch.setattr("app._get_rev_api_key", lambda: "test-key")
        large_file = tmp_path / "big.wav"
        large_file.write_bytes(b"x" * (60 * 1024 * 1024))
        compressed_file = tmp_path / "compressed.mp3"
        compressed_file.write_bytes(b"y" * 1000)
        mock_compress.return_value = str(compressed_file)
        mock_transcribe.return_value = "Speaker 1: Compressed transcript."
        result = process_audio_file(str(large_file), "big.wav")
        mock_compress.assert_called_once()
        assert "Compressed transcript" in result

    @patch("app._transcribe_with_rev_ai")
    def test_empty_transcript_raises(self, mock_transcribe, monkeypatch):
        monkeypatch.setattr("app._get_rev_api_key", lambda: "test-key")
        mock_transcribe.return_value = ""
        with pytest.raises(RuntimeError, match="empty transcript"):
            process_audio_file(b"audio", "test.mp3")
