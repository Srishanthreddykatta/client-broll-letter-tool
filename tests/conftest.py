import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app


@pytest.fixture
def app():
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_txt_cut_sheet():
    return b"""=== Cut Sheet: Episode 1 ===
Timestamp\tSegment\tType\tNotes
00:00-00:30\tIntroduction\tIP\tMarcus talks about growing up in Detroit
00:30-01:15\tChildhood\tIP\tMarcus: "I grew up on the east side of Detroit. We didn't have much, but my grandmother made sure we had values."
01:15-02:00\tEarly Career\tIP\tMarcus: "I started my first business at 22 with nothing but a laptop and a dream. Nobody believed in me."
02:00-03:00\tStruggle\tIP\tMarcus: "There were nights I couldn't pay rent. I slept in my car for three months. But I refused to quit."
03:00-04:00\tBreakthrough\tIP\tMarcus: "When that first big contract came in, I cried. Not because of the money, but because someone finally saw my vision."
04:00-05:00\tFamily\tIP\tMarcus: "My wife stood by me through all of it. She never once told me to give up."
05:00-06:00\tCurrent Day\tIP\tMarcus: "Now I employ 47 people. Every single one of them reminds me why I kept going."
06:00-06:30\tClosing\tVO\tNarration about legacy and purpose
"""


@pytest.fixture
def sample_xlsx_bytes():
    import openpyxl
    import io
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cut Sheet"
    ws.append(["Timestamp", "Segment", "Type", "Notes"])
    ws.append(["00:00-00:30", "Introduction", "IP", "Subject introduces themselves"])
    ws.append(["00:30-01:30", "Story", "IP", "Subject talks about childhood"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
