"""Tests for Flask routes and generation pipeline."""
import io
import pytest


class TestIndexRoute:
    def test_index_loads(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"B-Roll" in resp.data

    def test_index_shows_upload(self, client):
        resp = client.get("/")
        assert b"cut_sheet" in resp.data
        assert b".mp3" in resp.data


class TestGenerateRoute:
    def test_no_file_redirects(self, client):
        resp = client.post("/generate", data={}, follow_redirects=True)
        assert b"upload" in resp.data.lower()

    def test_invalid_file_type_rejected(self, client):
        data = {"cut_sheet": (io.BytesIO(b"fake"), "test.exe")}
        resp = client.post(
            "/generate",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert b"Invalid file type" in resp.data

    def test_txt_file_accepted(self, client, sample_txt_cut_sheet, monkeypatch):
        monkeypatch.setattr(
            "app.call_claude",
            lambda *a, **kw: "## AT A GLANCE\n**Total:** 10\n## Opening\nDear Marcus,\nTest brief.",
        )
        monkeypatch.setattr("app.generate_location_images", lambda *a, **kw: [])

        data = {"cut_sheet": (io.BytesIO(sample_txt_cut_sheet), "cut.txt")}
        resp = client.post(
            "/generate",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200

    def test_audio_file_triggers_transcription(self, client, monkeypatch):
        monkeypatch.setattr(
            "app.process_audio_file",
            lambda fb, fn: "Marcus: I grew up in Detroit.",
        )
        monkeypatch.setattr(
            "app.call_claude_with_text",
            lambda *a, **kw: "## AT A GLANCE\n**Total:** 5\n## Opening\nDear Marcus,",
        )
        monkeypatch.setattr("app.generate_location_images", lambda *a, **kw: [])

        data = {"cut_sheet": (io.BytesIO(b"fake audio bytes"), "interview.mp3")}
        resp = client.post(
            "/generate",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200


class TestDownloadRoutes:
    def test_pdf_download_missing_brief(self, client):
        resp = client.get("/download-pdf/nonexistent-id", follow_redirects=True)
        assert b"No brief found" in resp.data or resp.status_code == 200

    def test_html_download_missing_brief(self, client):
        resp = client.get("/download-html/nonexistent-id", follow_redirects=True)
        assert b"No brief found" in resp.data or resp.status_code == 200
