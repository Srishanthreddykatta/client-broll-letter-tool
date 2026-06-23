"""
Client B-Roll brief formatting: sanitize text, match reference .docx styling,
and build export-ready HTML (Arial, gold table headers, no image section).
"""

import os
from pathlib import Path
import re
import markdown

# Emoji and symbols that break Word / Google Docs paste
UNSAFE_SYMBOLS_RE = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF"
    r"\u2713\u2714\u2611\u25CE\u24D8\U0001F4CC\u27A1\u27A4\u2192\u2193\u2190"
    r"\u2022\u25CF\u25CB\u25A0\u25AA\u2605\u2606\u2728\u2705\u274C\u274E"
    r"\uFE0F]+",
    flags=re.UNICODE,
)

CELL_PREFIX_RE = re.compile(
    r"^\s*(?:"
    r"[\u2713\u2714]\s*)?"
    r"(?:Quick|Better)\s*:\s*",
    re.IGNORECASE,
)

VISUAL_REFERENCE_SECTION_RE = re.compile(
    r"(?im)^#{1,3}\s*SECTION:\s*VISUAL\s+REFERENCE\s+IMAGES.*?"
    r"(?=^#{1,3}\s*SECTION:\s*(?!VISUAL)|\Z)",
    re.DOTALL | re.MULTILINE,
)

VISUAL_REFERENCES_ALT_RE = re.compile(
    r"(?im)^#{1,3}\s*Visual\s+References.*?"
    r"(?=^#{1,3}\s|\Z)",
    re.DOTALL | re.MULTILINE,
)

REFERENCE_IMAGE_LINE_RE = re.compile(
    r"^\s*\[REFERENCE\s+IMAGE:.*?\]\s*$",
    re.IGNORECASE | re.MULTILINE,
)

IMAGE_PLACEHOLDER_LINE_RE = re.compile(
    r"^\s*\[IMAGE\s+PLACEHOLDER.*?\]\s*$",
    re.IGNORECASE | re.MULTILINE,
)

SECTION_A_RE = re.compile(
    r"(?is)(##\s*SECTION\s+A[^\n]*\n)(.*?)(?=\n---\s*\n|\n##\s*SECTION\s+B)",
)

SECTION_A_LINE_RE = re.compile(
    r"^\s*(\d+)\.\s*(.+?)\s+-\s+(.+?)\s*$",
    re.MULTILINE,
)

SECTION_A_CATEGORY_RE = re.compile(r"^\s*\*\*([A-Z][A-Z\s&]+)\*\*\s*$", re.MULTILINE)

PHOTO_CONTEXT_SECTION_RE = re.compile(
    r"(?is)(##\s*SECTION:\s*PHOTO\s+CONTEXT[^\n]*\n)(.*?)(?=\n---\s*\n|\n##\s*SECTION:\s*VIDEO)",
)

PHOTO_CONTEXT_ITEM_RE = re.compile(
    r"^\*\*(\d+)\.\s*(.+?)\s*[—–-]\*\*\s*\n+"
    r"\s*(?:\*\"(.*?)\"\*|\"(.*?)\")\s*(.+?)(?=\n\*\*|\Z)",
    re.MULTILINE | re.DOTALL,
)

VIDEO_SHOTS_SECTION_RE = re.compile(
    r"(?is)(##\s*SECTION:\s*VIDEO\s+SHOT\s+DETAILS[^\n]*\n)(.*?)(?=\n---\s*\n|\n##\s*SECTION:\s*VIDEOGRAPHER)",
)

VIDEO_SHOT_ROW_RE = re.compile(
    r"\|\s*\*\*Shot\s*(\d+)\s*·\s*([^|*]+?)\*\*\s*"
    r"(?:\*([^*|]+?)\*|([^|*]+?))\s*\|\s*"
    r"\*\*Before:\*\*\s*\*\"(.*?)\"\*\s*\*\*Mood:\*\*\s*(.+?)\s*\|",
    re.IGNORECASE | re.DOTALL,
)

FORMAT_HINT_LINE_RE = re.compile(
    r"^_Format:.*?_\s*\n+",
    re.IGNORECASE | re.MULTILINE,
)

# Reference palette — black headers/boxes, white bold text
COLOR_HEADER = "#000000"
COLOR_HEADER_TEXT = "#FFFFFF"
COLOR_CATEGORY_A = "#000000"
COLOR_CATEGORY_B = "#000000"
COLOR_CATEGORY_C = "#000000"
COLOR_ROW_ALT = "#FAFAF5"
COLOR_ROW_NUM = "#FDF8F0"
COLOR_QUICK_COL = "#F9FDF4"
COLOR_PRO_COL = "#F5F8FF"
COLOR_BORDER = "#000000"

CATEGORY_NAMES = frozenset({
    "CHILDHOOD", "CAREER", "FAMILY", "IMPACT", "COMMUNITY",
    "RECOGNITION", "STORY", "POOL", "HOW TO SUBMIT",
    "INSTRUCTIONS FOR THE CLIENT", "FOLDER",
})

SPECIFIC_AGE_RE = re.compile(
    r"\b(?:around |at |approximately )?age\s+(\d+)\b",
    re.IGNORECASE,
)

PHOTO_AGE_SIX_RE = re.compile(
    r"\b(?:photo of you )?around age\s*6\b",
    re.IGNORECASE,
)


def _age_to_range(age: int) -> str:
    if age <= 12:
        low, high = max(2, age - 2), age + 2
        return f"early childhood (roughly ages {low}–{high})"
    if age <= 18:
        low, high = max(13, age - 2), min(19, age + 2)
        return f"your teens (roughly ages {low}–{high})"
    if age <= 29:
        low, high = max(18, age - 3), age + 3
        return f"your twenties (roughly ages {low}–{high})"
    if age <= 39:
        low, high = age - 3, age + 3
        return f"your thirties (roughly ages {low}–{high})"
    low, high = age - 4, age + 4
    return f"roughly ages {low}–{high}"


def _generalize_ages_in_text(text: str) -> str:
    """Replace specific ages with broad ranges (client-friendly guidance)."""
    if not text:
        return text

    def repl(match: re.Match) -> str:
        return _age_to_range(int(match.group(1)))

    text = re.sub(
        r"\bPhoto of you around age\s*\d+\b",
        "Childhood photo (early childhood years)",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bIdeally around age\s*\d+\b",
        "You in early childhood (roughly ages 4–8)",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bYou around age\s*\d+\b",
        "You in early childhood (roughly ages 4–8)",
        text,
        flags=re.IGNORECASE,
    )
    return SPECIFIC_AGE_RE.sub(repl, text)


LOGO_HTML_WIDTH = 64
LOGO_HTML_HEIGHT = 45
LOGO_DOCX_MAX_WIDTH_PT = 52.0

SECTION_B_ARCHIVAL_RE = re.compile(
    r"(?is)(##\s*SECTION\s+B\s*[—–-]\s*VIDEOS?\s*&\s*ARCHIVAL[^\n]*\n)(.*?)(?=\n---\s*\n|\n##\s*SECTION\s+C)",
)

SECTION_B_V2_HEADERS = (
    "| **Video** | **A little more detail** | **Good to have** | **Alternative option** |"
)


def _has_section_b_archival(brief_md: str) -> bool:
    return bool(
        re.search(
            r"##\s*SECTION\s+B\s*[—–-]\s*VIDEOS?\s*&\s*ARCHIVAL",
            brief_md or "",
            re.IGNORECASE,
        )
    )


def _extract_section_a_categories(brief_md: str) -> list[str]:
    match = SECTION_A_RE.search(brief_md or "")
    if not match:
        return []
    cats: list[str] = []
    for line in match.group(2).splitlines():
        cat = re.match(r"^\|\s*\*\*([A-Z][A-Z\s&]+)\*\*\s*\|", line.strip())
        if cat:
            cats.append(cat.group(1).strip().title())
    return cats


def _extract_section_b_video_labels(brief_md: str) -> list[str]:
    match = SECTION_B_ARCHIVAL_RE.search(brief_md or "")
    if not match:
        return []
    labels: list[str] = []
    for line in match.group(2).splitlines():
        row = PHOTO_V2_DATA_ROW_RE.match(line.strip())
        if not row:
            continue
        label = row.group(1).strip()
        if label.startswith("**") or re.match(r"^-+$", label):
            continue
        labels.append(label)
    return labels


def _photo_label_to_video_label(photo_label: str) -> str:
    lower = photo_label.lower()
    if "childhood" in lower:
        return "Childhood home video"
    if "hometown" in lower:
        return "Hometown video"
    label = re.sub(r"\s+photo$", "", photo_label.strip(), flags=re.IGNORECASE)
    if not re.search(r"\bvideo\b", label, re.IGNORECASE):
        label = f"{label} video"
    return label[0].upper() + label[1:] if label else photo_label


def _video_archival_ideal(photo_label: str, _photo_detail: str = "") -> str:
    lower = photo_label.lower()
    if "childhood" in lower:
        return "Home video or clips from your early childhood years"
    if "hometown" in lower:
        return "Footage of your hometown, neighbourhood, or where you grew up"
    if "medical career" in lower or ("medical" in lower and "care" not in lower):
        return "Training, hospital, or early career footage you may have saved"
    if "clinic" in lower or "newu" in lower or "headquarters" in lower:
        return "Video of your practice, building, or workspace over the years"
    if "grandfather" in lower and "banjo" not in lower:
        return "Family footage with your grandfather if you have it"
    if "banjo" in lower:
        return "Video of him playing or clips showing the banjo"
    if "daughter" in lower or "mackenzie" in lower:
        return "Family videos with your daughter at any age"
    if "healing hands" in lower:
        return "Clips of the project, packing kits, or events"
    if "award" in lower or "press" in lower:
        return "News clips, award ceremonies, or media appearances"
    if "patient" in lower or "care" in lower:
        return "Privacy-safe clinical or practice footage (no patient IDs)"
    return "Any saved video that represents this moment in your story"


def _video_archival_good_to_have(photo_label: str) -> str:
    lower = photo_label.lower()
    if "childhood" in lower or "hometown" in lower:
        return "Clips that represent where you came from"
    if "grandfather" in lower or "daughter" in lower or "banjo" in lower or "family" in lower:
        return "Clips that represent family and relationships"
    if (
        "career" in lower
        or "medical" in lower
        or "clinic" in lower
        or "newu" in lower
        or "patient" in lower
    ):
        return "Clips that show your professional journey"
    if "healing" in lower or "impact" in lower or "award" in lower:
        return "Clips that show your impact or recognition"
    return "Any footage that still tells this part of your story"


def _video_archival_alternative(photo_label: str, photo_alt: str) -> str:
    if photo_alt:
        alt = (
            photo_alt.replace("Photos", "Footage")
            .replace("photos", "footage")
            .replace("photo", "clip")
            .replace("image", "clip")
            .replace("Images", "Footage")
        )
        return alt
    lower = photo_label.lower()
    if "childhood" in lower or "hometown" in lower:
        return "Similar-era home video or neighbourhood footage"
    if "grandfather" in lower or "banjo" in lower:
        return "Any family gathering video from that era"
    if "daughter" in lower or "mackenzie" in lower:
        return "Mother-daughter or family home video clip"
    if "clinic" in lower or "newu" in lower:
        return "Office event footage or team celebration clip"
    return "Legacy clip from the same chapter of your life"


def _build_section_b_archival_table(entries: list[tuple[str | None, str, str]]) -> str:
    rows = [SECTION_B_V2_HEADERS, "|---|---|---|---|"]
    last_cat = None
    for cat, item, alt_detail in entries:
        if cat and cat != last_cat:
            rows.append(f"| **{cat}** | | | |")
            last_cat = cat
        photo = _short_photo_label(_resolve_source_item(item))
        video = _photo_label_to_video_label(photo)
        ideal = _video_archival_ideal(photo, alt_detail)
        good = _video_archival_good_to_have(photo)
        alt = _video_archival_alternative(photo, alt_detail)
        rows.append(f"| {video} | {ideal} | {good} | {alt} |")
    return "\n".join(rows)


def _ensure_checklist_sections(brief_md: str) -> str:
    """Insert story-specific Section B (videos & archival) and renumber footage/interviews."""
    text = brief_md or ""
    if _has_section_b_archival(text):
        return text
    if not re.search(
        r"##\s*SECTION\s+B\s*[—–-]\s*NEW\s+VIDEO", text, re.IGNORECASE
    ):
        return text

    match_a = SECTION_A_RE.search(text)
    if not match_a:
        return text
    entries = _parse_section_a_rows(match_a.group(2))
    if not entries:
        return text

    table = _build_section_b_archival_table(entries)
    section_b = (
        f"## SECTION B — VIDEOS & ARCHIVAL ({len(entries)} items)\n\n"
        f"{table}\n\n---\n\n"
    )
    text = text[: match_a.end()] + "\n\n---\n\n" + section_b + text[match_a.end() :]

    text = re.sub(
        r"##\s*SECTION\s+B\s*[—–-]\s*NEW\s+VIDEO\s+FOOTAGE",
        "## SECTION C — NEW VIDEO FOOTAGE",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"##\s*SECTION\s+C\s*[—–-]\s*INTERVIEW(?:\s+CLIPS)?",
        "## SECTION D — INTERVIEW CLIPS",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    return text


def _folder_slug(name: str) -> str:
    text = name.strip().rstrip("/")
    return f"{text}/"


def _build_folder_structure_rows(client_name: str, brief_md: str) -> list[str]:
    """Compact folder tree — section folders + category subfolders (not every checklist item)."""
    root = f"{client_name} — B-Roll Upload/"
    categories = _extract_section_a_categories(brief_md) or [
        "Childhood",
        "Career",
        "Family",
        "Impact",
    ]
    sections: list[tuple[str, list[str]]] = [
        ("Section A — Photos & Archival", categories),
        ("Section B — Videos & Archival", categories),
        ("Section C — New Video Footage", ["Story shots", "Pool shots"]),
        ("Section D — Interviews", ["Interview 1", "Interview 2"]),
    ]

    lines = [f"**{root}**"]
    for si, (title, subs) in enumerate(sections):
        sec_last = si == len(sections) - 1
        lines.append(f"{'└──' if sec_last else '├──'} **{title}/**")
        indent = "    " if sec_last else "│   "
        for fi, sub in enumerate(subs):
            sub_last = fi == len(subs) - 1
            lines.append(f"{indent}{'└──' if sub_last else '├──'} {_folder_slug(sub)}")
    return lines


def _client_front_matter_md(client_full_name: str, brief_md: str | None = None) -> str:
    name = client_full_name or "Client"
    md = brief_md or ""
    folder_lines = _build_folder_structure_rows(name, md)
    folder_table = "\n".join(f"| {line} |" for line in folder_lines)
    return f"""# MUST READ — INSTRUCTIONS FOR THE CLIENT

| **MUST READ** |
|---|
| Work through the checklist on page 2 (Sections A–D). Gather what you can; use alternatives when noted. |
| **File naming:** childhood_photo_1.jpg, morning_ritual_1.mp4 — up to **3 options per photo**. Unlabelled files may not be used. |
| **Section E — Extras:** one folder for substitutes or bonus clips. Label clearly (_1, _2, _3 for options). |

| **Your upload folder tree** |
|---|
{folder_table}

| **How to submit** |
|---|
| Create the folders above inside your upload |
| Google Drive or Dropbox · sharing: anyone with the link can view |
| Email subject: {name} — B-Roll Submission · Questions? Reply to your Inside Success contact |

"""


def _remove_duplicate_submit_section(brief_md: str) -> str:
    """Remove footer HOW TO SUBMIT — it now lives in the front-matter block."""
    return re.sub(
        r"\n---\s*\n##\s*SECTION\s+D\s*[—–-]\s*HOW TO SUBMIT.*?(?=\n---\s*\n#|\n#\s*DETAILED)",
        "\n---\n",
        brief_md or "",
        count=1,
        flags=re.DOTALL | re.IGNORECASE,
    )


def _strip_existing_front_matter(brief_md: str) -> str:
    """Remove prior instructions/folder/submit block so we can inject the current template."""
    text = brief_md or ""
    text = re.sub(
        r"^#\s*(?:MUST READ\s*[—–-]\s*)?INSTRUCTIONS FOR THE CLIENT\b.*?(?=^#\s*QUICK\s+CHECKLIST)",
        "",
        text,
        count=1,
        flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    return text.lstrip()


def _ensure_client_front_matter(brief_md: str, client_full_name: str) -> str:
    """Inject must-read instructions, folder structure, and how-to-submit before the checklist."""
    text = _remove_duplicate_submit_section(brief_md or "")
    text = _strip_existing_front_matter(text)
    front = _client_front_matter_md(client_full_name, text)
    text = re.sub(
        r"^#\s*PAGE\s*1\s*[—–-]\s*",
        "# ",
        text,
        count=1,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    if re.search(r"^#\s*QUICK\s+CHECKLIST", text, re.MULTILINE | re.IGNORECASE):
        return re.sub(
            r"^(#\s*QUICK\s+CHECKLIST)",
            front + r"\1",
            text,
            count=1,
            flags=re.MULTILINE | re.IGNORECASE,
        )
    return front + text


def sanitize_brief_markdown(brief_md: str) -> str:
    """Remove emojis, cell prefixes, and the visual reference images section."""
    text = brief_md or ""
    text = remove_visual_reference_section(text)
    text = REFERENCE_IMAGE_LINE_RE.sub("", text)
    text = IMAGE_PLACEHOLDER_LINE_RE.sub("", text)
    text = FORMAT_HINT_LINE_RE.sub("", text)
    text = _ensure_section_a_table(text)
    text = _ensure_photo_context_table(text)
    text = _ensure_video_shots_table(text)
    lines = []
    for line in text.splitlines():
        line = UNSAFE_SYMBOLS_RE.sub("", line)
        if line.strip().startswith("|"):
            parts = line.split("|")
            line = "|".join(
                CELL_PREFIX_RE.sub("", UNSAFE_SYMBOLS_RE.sub("", part)) for part in parts
            )
        else:
            line = CELL_PREFIX_RE.sub("", line)
        lines.append(line)
    text = "\n".join(lines)
    text = re.sub(
        r"\|\s*\*\*Better option \(professional\)\*\*\s*\|",
        "| **Professional option** |",
        text,
        flags=re.IGNORECASE,
    )
    text = _ensure_closing_paragraph(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def remove_visual_reference_section(brief_md: str) -> str:
    text = brief_md or ""
    text = VISUAL_REFERENCE_SECTION_RE.sub("", text)
    text = VISUAL_REFERENCES_ALT_RE.sub("", text)
    return text


PHOTO_TABLE_DATA_ROW_RE = re.compile(
    r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
    re.MULTILINE,
)

PHOTO_SCHEMA_TEMPLATE = "[Item] [A little more detail] [alternative] [alternative detail]"

PHOTO_SCHEMA_LINE_RE = re.compile(
    r"^\s*(.+?)\s+-\s+.+?\s+-\s+.+?\s+\(ex\.\s*(.+?)\)\s*$"
)


def _ensure_section_a_table(brief_md: str) -> str:
    """Section A: three-column table with category rows."""
    match = SECTION_A_RE.search(brief_md)
    if not match:
        return brief_md
    body = match.group(2)
    if "| **#" in body and "**What to find**" in body:
        return brief_md

    rows = [
        "| **#** | **What to find** | **Don't have it? Use this instead** |",
        "|---|---|---|",
    ]
    item_num = 0
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("|---"):
            continue
        if line == PHOTO_SCHEMA_TEMPLATE or line.startswith("[Item]"):
            continue
        cat_in_table = re.match(r"^\|\s*\*\*([A-Z][A-Z\s&]+)\*\*\s*\|", line)
        if cat_in_table:
            rows.append(f"| **{cat_in_table.group(1).strip()}** | | |")
            continue
        row = PHOTO_TABLE_DATA_ROW_RE.match(line)
        if row:
            rows.append(f"| {row.group(1)} | {row.group(2).strip()} | {row.group(3).strip()} |")
            item_num = max(item_num, int(row.group(1)))
            continue
        if line.startswith("| **#"):
            continue
        cat = SECTION_A_CATEGORY_RE.match(line)
        if cat:
            rows.append(f"| **{cat.group(1).strip()}** | | |")
            continue
        schema = PHOTO_SCHEMA_LINE_RE.match(line)
        if schema:
            item_num += 1
            rows.append(f"| {item_num} | {schema.group(1).strip()} | {schema.group(2).strip()} |")
            continue
        numbered = SECTION_A_LINE_RE.match(line)
        if numbered:
            rows.append(f"| {numbered.group(1)} | {numbered.group(2).strip()} | {numbered.group(3).strip()} |")
            item_num = max(item_num, int(numbered.group(1)))

    if len(rows) <= 2:
        return brief_md

    new_section = match.group(1).rstrip() + "\n\n" + "\n".join(rows) + "\n"
    return brief_md[: match.start()] + new_section + brief_md[match.end() :]


PHOTO_V2_DATA_ROW_RE = re.compile(
    r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
    re.MULTILINE,
)

# Section A v2 — client-friendly headers (matches brief schema)
SECTION_A_V2_HEADERS = (
    "| **Photo** | **A little more detail** | **Good to have** | **Alternative option** |"
)

TABLE_CELL_PADDING = "3px 5px"
TABLE_CELL_PADDING_COMPACT = "2px 4px"
TABLE_FONT_SIZE = "9.5pt"
TABLE_FONT_SIZE_COMPACT = "8.5pt"
TABLE_MARGIN = "5px 0"

# Heuristic layout for Word/DOCX page breaks (compact 9.5pt tables)
ROWS_PER_PAGE = 26
PAGE_TOP_MAX_ROWS = int(ROWS_PER_PAGE * 2 / 5)  # top 2/5 of page — continue next section here
DOC_HEADER_ROW_UNITS = 4
PREAMBLE_ROW_UNITS = 4
SECTION_HEADING_ROW_UNITS = 2
DETAILED_CONTEXT_BLOCK_ROWS = 4
# Minimum rows left on a page to start Section B (heading + table header + category + rows)
MIN_ROWS_TO_START_SECTION_B = 10

WORD_PAGE_BREAK_STYLE = "page-break-before:always;mso-page-break-before:always;"

CLOSING_SECTION_RE = re.compile(
    r"(?is)(##\s*SECTION:\s*CLOSING\s*\n+)\s*\|(.+?)\|\s*(?=\Z|\n---)",
)

# Map full cut-sheet item text -> short Photo column label (always includes "photo" when relevant)
PHOTO_SOURCE_TO_LABEL = {
    "childhood photo (early childhood years)": "Childhood photo",
    "photo of you around age 6": "Childhood photo",
    "photo of your hometown / childhood setting": "Hometown photo",
    "early medical career photo (scrubs/hospital)": "Early medical career photo",
    "photo of first newu clinic (1800 sq ft)": "First NewU clinic photo",
    "current newu headquarters exterior": "NewU headquarters photo",
    "you with patients or in clinical setting": "Patient care photo",
    "photo with your grandfather": "Grandfather photo",
    "his banjo (close-up if you have it)": "Grandfather's banjo photo",
    "photo with daughter mackenzie (any age)": "Daughter Mackenzie photo",
    "healing hands project in action": "Healing Hands Project photo",
    "award, recognition, or press coverage": "Award or press photo",
}

# Reverse map + legacy v2 labels so we can rebuild from an older v2 table
PHOTO_LABEL_TO_SOURCE = {v.lower(): k for k, v in PHOTO_SOURCE_TO_LABEL.items()}
PHOTO_LABEL_TO_SOURCE.update({
    "hometown / childhood setting": "photo of your hometown / childhood setting",
    "early medical career": "early medical career photo (scrubs/hospital)",
    "first newu clinic": "photo of first newu clinic (1800 sq ft)",
    "newu headquarters exterior": "current newu headquarters exterior",
    "patient care setting": "you with patients or in clinical setting",
    "photo with grandfather": "photo with your grandfather",
    "grandfather's banjo": "his banjo (close-up if you have it)",
    "photo with daughter mackenzie": "photo with daughter mackenzie (any age)",
    "healing hands project": "healing hands project in action",
    "award or press coverage": "award, recognition, or press coverage",
})


def _resolve_source_item(item_or_label: str) -> str:
    """Normalize to full source line for ideal/alternative text generation."""
    text = re.sub(r"\*\*", "", item_or_label).strip()
    key = text.lower()
    if key in PHOTO_SOURCE_TO_LABEL:
        return text
    if key in PHOTO_LABEL_TO_SOURCE:
        return PHOTO_LABEL_TO_SOURCE[key]
    return text


def _short_photo_label(item: str) -> str:
    """Readable photo name for the first column."""
    source = _resolve_source_item(item)
    source = re.sub(r"^\d+\.\s*", "", source.strip())
    key = source.lower()
    if key in PHOTO_SOURCE_TO_LABEL:
        return PHOTO_SOURCE_TO_LABEL[key]
    label = re.sub(r"^Photo of (you |your )?", "", source, flags=re.IGNORECASE)
    label = re.sub(r"^You with ", "", label, flags=re.IGNORECASE)
    if label and "photo" not in label.lower():
        label = f"{label} photo"
    return label[0].upper() + label[1:] if label else item


def _photo_ideal_version(item: str) -> str:
    lower = item.lower()
    if "age 6" in lower or "childhood photo" in lower or "early childhood years" in lower:
        return "You in early childhood (roughly ages 4–8)"
    if "hometown" in lower or "childhood setting" in lower:
        return "Photo of your hometown area or where you grew up"
    if "grandfather" in lower:
        return "Ideally with him in the photo"
    if "banjo" in lower:
        return "Close-up of the banjo is fine"
    if "mackenzie" in lower or "daughter" in lower:
        return "Any age that feels right to you"
    if "healing hands" in lower:
        return "Project in action or supplies being prepared"
    if "award" in lower or "press" in lower:
        return "Award, article, or media feature"
    if "first newu" in lower or "1800" in lower:
        return "Your first clinic space"
    if "headquarters" in lower or "exterior" in lower:
        return "Current building exterior"
    if "medical career" in lower or "scrubs" in lower:
        return "Early training or hospital era"
    if "patients" in lower or "clinical" in lower:
        return "You in a care setting (privacy-safe)"
    return "Best version you have available"


def _photo_alternative_guidance(item: str) -> str:
    lower = item.lower()
    if "age 6" in lower or ("childhood" in lower and "photo" in lower):
        return "Photos that represent your childhood"
    if "hometown" in lower or "childhood setting" in lower:
        return "Photos that represent where you grew up"
    if "grandfather" in lower:
        return "Photos that represent his role in your life"
    if "banjo" in lower:
        return "Photos that represent that legacy object"
    if "daughter" in lower or "mackenzie" in lower:
        return "Photos that represent your relationship with her"
    if "healing hands" in lower:
        return "Images that show the project or its impact"
    if "award" in lower or "press" in lower:
        return "Materials that show recognition you have received"
    if "clinic" in lower or "newu" in lower or "headquarters" in lower:
        return "Images that represent your practice or workspace"
    if "medical" in lower or "career" in lower:
        return "Images that represent your medical journey"
    if "patients" in lower:
        return "Images that represent your approach to patient care"
    return "Alternative image that still tells this part of your story"


def _parse_section_a_rows(body: str) -> list[tuple[str | None, str, str]]:
    """Return list of (category or None, source item, alternative_detail text)."""
    entries = []
    current_cat = None
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("|---"):
            continue
        cat = re.match(r"^\|\s*\*\*([A-Z][A-Z\s&]+)\*\*\s*\|", line)
        if cat:
            current_cat = cat.group(1).strip()
            continue
        cat_line = SECTION_A_CATEGORY_RE.match(line)
        if cat_line:
            current_cat = cat_line.group(1).strip()
            continue
        v1 = PHOTO_TABLE_DATA_ROW_RE.match(line)
        if v1:
            entries.append((current_cat, v1.group(2).strip(), v1.group(3).strip()))
            continue
        v2 = PHOTO_V2_DATA_ROW_RE.match(line)
        if v2:
            label = v2.group(1).strip()
            if label.startswith("**Photo") or label.startswith("**Ideal"):
                continue
            detail = v2.group(4).strip()
            entries.append((current_cat, label, detail))
            continue
        if line.startswith("| **#") or line.startswith("| **Photo"):
            continue
    return entries


def _ensure_section_a_v2_table(brief_md: str) -> str:
    """Section A v2: Photo | Ideal detail | Alternative (good to have) | Alternative detail."""
    match = SECTION_A_RE.search(brief_md)
    if not match:
        return brief_md
    body = match.group(2)
    if "**Good to have**" in body and "**Alternative option**" in body:
        return brief_md

    entries = _parse_section_a_rows(body)
    if not entries:
        return brief_md

    rows = [SECTION_A_V2_HEADERS, "|---|---|---|---|"]
    last_cat = None
    for cat, item, alt_detail in entries:
        if cat and cat != last_cat:
            rows.append(f"| **{cat}** | | | |")
            last_cat = cat
        source = _resolve_source_item(item)
        photo = _short_photo_label(source)
        ideal = _photo_ideal_version(source)
        alt = _photo_alternative_guidance(source)
        detail = alt_detail.replace("|", "/")
        rows.append(f"| {photo} | {ideal} | {alt} | {detail} |")

    new_section = match.group(1).rstrip() + "\n\n" + "\n".join(rows) + "\n"
    return brief_md[: match.start()] + new_section + brief_md[match.end() :]


def _strip_section_count_footers(brief_md: str) -> str:
    """Remove redundant 'A | PHOTOS (N items)' lines after checklist tables."""
    return re.sub(
        r"^\*\*[A-D]\s*\|\s*.+?\s*\([^)]+\)\*\*\s*\n?",
        "",
        brief_md or "",
        flags=re.MULTILINE | re.IGNORECASE,
    )


def _normalize_brief_layout(brief_md: str) -> str:
    """Clean page labels, page-2 title, and extra breaks before export."""
    text = brief_md or ""
    text = re.sub(
        r"^#\s*PAGE\s*1\s*[—–-]\s*",
        "# ",
        text,
        count=1,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    text = re.sub(
        r"^#\s*PAGE\s*2\s*[—–-]\s*",
        "# ",
        text,
        count=1,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    text = re.sub(
        r"^\*Share page 2 with your videographer.*\*",
        "*Share this page with your videographer. This page explains why each shot matters.*",
        text,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    text = re.sub(r"(\n---\s*){2,}(\n#\s*DETAILED)", r"\n---\2", text, flags=re.IGNORECASE)
    text = _strip_section_count_footers(text)
    text = re.sub(
        r"^# QUICK CHECKLIST\s*\n+\*Scan this page first\.[^*]*\*\s*\n+---\s*\n+",
        "# QUICK CHECKLIST\n\n",
        text,
        count=1,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    text = _ensure_closing_paragraph(text)
    text = _generalize_ages_in_text(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _ensure_closing_paragraph(brief_md: str) -> str:
    """Replace single-row pipe table under CLOSING with a plain paragraph (avoids | in DOCX)."""

    def repl(match: re.Match) -> str:
        body = match.group(2).strip()
        return match.group(1) + body + "\n"

    return CLOSING_SECTION_RE.sub(repl, brief_md)


def _is_table_separator_line(line: str) -> bool:
    s = line.strip()
    if not s.startswith("|"):
        return False
    inner = s.replace("|", "").replace("-", "").replace(":", "").strip()
    return not inner


def _count_markdown_table_rows(text: str) -> int:
    count = 0
    for line in (text or "").splitlines():
        s = line.strip()
        if not s.startswith("|") or _is_table_separator_line(s):
            continue
        count += 1
    return count


def _count_prose_row_units(text: str) -> int:
    units = 0
    for line in (text or "").splitlines():
        s = line.strip()
        if not s or s.startswith("|") or s.startswith("---"):
            continue
        if s.startswith("#"):
            units += 1
        elif len(s) > 3:
            units += 1
    return units


def _position_on_page(total_rows: int, rows_per_page: int = ROWS_PER_PAGE) -> int:
    if total_rows <= 0:
        return 0
    pos = total_rows % rows_per_page
    return pos if pos else rows_per_page


def _rows_remaining_on_page(total_rows: int) -> int:
    """Estimated empty row-units left on the page where content currently ends."""
    if total_rows <= 0:
        return ROWS_PER_PAGE
    if total_rows <= ROWS_PER_PAGE:
        return ROWS_PER_PAGE - total_rows
    return ROWS_PER_PAGE - _position_on_page(total_rows)


def _needs_page_break_before_next(
    total_rows_after_previous: int,
    min_rows_needed: int = 2,
) -> bool:
    """
    Break before the next section unless the previous block ended in the top 2/5 of
    the current page AND there is enough room for min_rows_needed more content.
    """
    remaining = _rows_remaining_on_page(total_rows_after_previous)
    if total_rows_after_previous > ROWS_PER_PAGE:
        pos = _position_on_page(total_rows_after_previous)
        if pos > PAGE_TOP_MAX_ROWS:
            return True
        return remaining < min_rows_needed
    return remaining < min_rows_needed


def _extract_between(md: str, start_pat: str, end_pat: str) -> str:
    start = re.search(start_pat, md, re.IGNORECASE)
    if not start:
        return ""
    rest = md[start.end() :]
    end = re.search(end_pat, rest, re.IGNORECASE)
    return rest[: end.start()] if end else rest


def _build_page_break_plan(brief_md: str) -> dict[str, bool]:
    """Estimate where hard page breaks help DOCX layout."""
    md = brief_md or ""
    plan: dict[str, bool] = {
        "quick_checklist": True,
        "detailed_context": True,
        "section_b": False,
        "section_c": False,
        "section_d": False,
        "photo_context": False,
        "video_shots": False,
        "videographer": False,
    }

    y = DOC_HEADER_ROW_UNITS + PREAMBLE_ROW_UNITS

    a_body = _extract_between(md, r"##\s*SECTION\s+A", r"##\s*SECTION\s+B")
    y += SECTION_HEADING_ROW_UNITS + _count_markdown_table_rows(a_body)
    plan["section_b"] = _needs_page_break_before_next(y, MIN_ROWS_TO_START_SECTION_B)

    b_body = _extract_between(md, r"##\s*SECTION\s+B", r"##\s*SECTION\s+C")
    y += SECTION_HEADING_ROW_UNITS + _count_markdown_table_rows(b_body)
    plan["section_c"] = _needs_page_break_before_next(y, MIN_ROWS_TO_START_SECTION_B)

    c_body = _extract_between(md, r"##\s*SECTION\s+C", r"##\s*SECTION\s+D")
    y += SECTION_HEADING_ROW_UNITS + _count_markdown_table_rows(c_body)
    plan["section_d"] = _needs_page_break_before_next(y, MIN_ROWS_TO_START_SECTION_B)

    d_body = _extract_between(md, r"##\s*SECTION\s+D", r"#\s*DETAILED\s+CONTEXT")
    y += SECTION_HEADING_ROW_UNITS + _count_markdown_table_rows(d_body)

    y2 = DETAILED_CONTEXT_BLOCK_ROWS
    page2_specs = [
        ("photo_context", r"##\s*SECTION:\s*PHOTO\s+CONTEXT", r"##\s*SECTION:\s*VIDEO\s+SHOT"),
        ("video_shots", r"##\s*SECTION:\s*VIDEO\s+SHOT", r"##\s*SECTION:\s*VIDEOGRAPHER"),
        ("videographer", r"##\s*SECTION:\s*VIDEOGRAPHER", r"##\s*SECTION:\s*CLOSING"),
    ]
    for plan_key, heading, next_start in page2_specs:
        body = _extract_between(md, heading, next_start)
        y2 += SECTION_HEADING_ROW_UNITS + _count_markdown_table_rows(body) + _count_prose_row_units(body)
        plan[plan_key] = _needs_page_break_before_next(y2)

    return plan


def _heading_with_page_break(heading_html: str) -> str:
    """Inline Word/MSO page-break on heading (survives HTML → DOCX better than empty divs)."""
    if re.search(r"\bstyle\s*=", heading_html, re.IGNORECASE):
        return re.sub(
            r'\bstyle\s*=\s*["\']([^"\']*)["\']',
            lambda m: f'style="{m.group(1)}{WORD_PAGE_BREAK_STYLE}"',
            heading_html,
            count=1,
            flags=re.IGNORECASE,
        )
    return re.sub(
        r"(<h[12][^>]*)>",
        rf'\1 style="{WORD_PAGE_BREAK_STYLE}">',
        heading_html,
        count=1,
        flags=re.IGNORECASE,
    )


def _insert_page_break_before(html: str, pattern: str) -> str:
    def repl(match: re.Match) -> str:
        return _heading_with_page_break(match.group(1))

    return re.sub(pattern, repl, html, count=1, flags=re.IGNORECASE)


def _apply_smart_page_breaks(html: str, brief_md: str) -> str:
    plan = _build_page_break_plan(brief_md)
    # Page 1 = instructions + folder tree + how to submit; page 2 = checklist (Section A)
    if plan.get("quick_checklist"):
        html = _insert_page_break_before(html, r"(<h1[^>]*>QUICK\s+CHECKLIST[^<]*</h1>)")
    if plan.get("section_b"):
        html = _insert_page_break_before(
            html, r"(<h2[^>]*>SECTION\s+B\s*[—–-]\s*VIDEOS?\s*&[^<]*</h2>)"
        )
    if plan.get("section_c"):
        html = _insert_page_break_before(
            html, r"(<h2[^>]*>SECTION\s+C\s*[—–-]\s*NEW\s+VIDEO[^<]*</h2>)"
        )
    if plan.get("section_d"):
        html = _insert_page_break_before(
            html, r"(<h2[^>]*>SECTION\s+D\s*[—–-]\s*INTERVIEW[^<]*</h2>)"
        )
    if plan.get("detailed_context"):
        html = _insert_page_break_before(html, r"(<h1[^>]*>DETAILED\s+CONTEXT[^<]*</h1>)")
    if plan.get("photo_context"):
        html = _insert_page_break_before(
            html, r"(<h2[^>]*>SECTION:\s*PHOTO\s+CONTEXT[^<]*</h2>)"
        )
    if plan.get("video_shots"):
        html = _insert_page_break_before(
            html, r"(<h2[^>]*>SECTION:\s*VIDEO\s+SHOT[^<]*</h2>)"
        )
    if plan.get("videographer"):
        html = _insert_page_break_before(
            html, r"(<h2[^>]*>SECTION:\s*VIDEOGRAPHER[^<]*</h2>)"
        )
    return html


def sanitize_brief_markdown_v2(brief_md: str) -> str:
    """Sanitize brief and apply Section A v2 photo table format."""
    text = _normalize_brief_layout(brief_md)
    text = remove_visual_reference_section(text)
    text = REFERENCE_IMAGE_LINE_RE.sub("", text)
    text = IMAGE_PLACEHOLDER_LINE_RE.sub("", text)
    text = FORMAT_HINT_LINE_RE.sub("", text)
    text = _generalize_ages_in_text(text)
    text = _ensure_section_a_v2_table(text)
    text = _ensure_checklist_sections(text)
    text = _ensure_photo_context_table(text)
    text = _ensure_video_shots_table(text)
    lines = []
    for line in text.splitlines():
        line = UNSAFE_SYMBOLS_RE.sub("", line)
        if line.strip().startswith("|"):
            parts = line.split("|")
            line = "|".join(
                CELL_PREFIX_RE.sub("", UNSAFE_SYMBOLS_RE.sub("", part)) for part in parts
            )
        else:
            line = CELL_PREFIX_RE.sub("", line)
        lines.append(line)
    text = "\n".join(lines)
    text = re.sub(
        r"\|\s*\*\*Better option \(professional\)\*\*\s*\|",
        "| **Professional option** |",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\|\s*Folder structure:.*?\|",
        "| Follow the Folder Structure section at the top of this brief when organizing your upload |",
        text,
        flags=re.IGNORECASE,
    )
    text = _remove_duplicate_submit_section(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def _ensure_photo_context_table(brief_md: str) -> str:
    """Page 2 photo context: single table (#, Photo, Episode quote, Why we need it)."""
    match = PHOTO_CONTEXT_SECTION_RE.search(brief_md)
    if not match:
        return brief_md
    body = match.group(2)
    if "| **#** |" in body and "**Episode quote**" in body:
        return brief_md

    rows = [
        "| **#** | **Photo** | **Episode quote** | **Why we need it** |",
        "|---|---|---|---|",
    ]
    lines = body.splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        cat = SECTION_A_CATEGORY_RE.match(line)
        if cat:
            rows.append(f"| **{cat.group(1).strip()}** | | | |")
            idx += 1
            continue
        item_hdr = re.match(r"^\*\*(\d+)\.\s*(.+?)\s*[—–-]\*\*\s*$", line)
        if item_hdr:
            num, label = item_hdr.group(1), item_hdr.group(2).strip()
            quote, why = "", ""
            idx += 1
            while idx < len(lines) and not lines[idx].strip():
                idx += 1
            if idx < len(lines):
                detail = lines[idx].strip()
                qm = re.match(
                    r'^(?:\*"(.*?)"\*|"(.*?)")\s*(.+)?$',
                    detail,
                    re.DOTALL,
                )
                if qm:
                    quote = (qm.group(1) or qm.group(2) or "").strip()
                    why = (qm.group(3) or "").strip()
                idx += 1
            quote = quote.replace("|", "/")
            why = why.replace("|", "/")
            rows.append(f'| {num} | {label} | "{quote}" | {why} |')
            continue
        idx += 1

    if len(rows) <= 2:
        return brief_md

    new_section = match.group(1).rstrip() + "\n\n" + "\n".join(rows) + "\n"
    return brief_md[: match.start()] + new_section + brief_md[match.end() :]


def _ensure_video_shots_table(brief_md: str) -> str:
    """Merge per-shot markdown tables into one three-column table."""
    match = VIDEO_SHOTS_SECTION_RE.search(brief_md)
    if not match:
        return brief_md
    body = match.group(2)

    sub_match = re.search(
        r"^\*\*Story Shots[^\n]*\*\*",
        body,
        re.MULTILINE | re.IGNORECASE,
    )
    sub_header = (sub_match.group(0).strip() + "\n\n") if sub_match else ""

    rows = [
        "| **Shot · Duration** | **Before (from episode)** | **Mood** |",
        "|---|---|---|",
    ]
    for m in VIDEO_SHOT_ROW_RE.finditer(body):
        num, name = m.group(1), m.group(2).strip()
        duration = (m.group(3) or m.group(4) or "").strip()
        quote = m.group(5).strip().replace("|", "/")
        mood = m.group(6).strip().replace("|", "/")
        shot_cell = f"**Shot {num} · {name}** *{duration}*"
        rows.append(f'| {shot_cell} | "{quote}" | {mood} |')

    if len(rows) <= 2:
        return brief_md

    new_section = match.group(1).rstrip() + "\n\n" + sub_header + "\n".join(rows) + "\n"
    return brief_md[: match.start()] + new_section + brief_md[match.end() :]


def _cell_style(
    bg: str,
    bold: bool = False,
    italic: bool = False,
    color: str = "#1A1A1A",
    compact: bool = True,
    front_matter: bool = False,
) -> str:
    weight = "bold" if bold else "normal"
    slant = "italic" if italic else "normal"
    if front_matter:
        padding = TABLE_CELL_PADDING_COMPACT
        size = TABLE_FONT_SIZE_COMPACT
        line_height = "1.2"
    else:
        padding = TABLE_CELL_PADDING if compact else "7px 10px"
        size = TABLE_FONT_SIZE if compact else "10pt"
        line_height = "1.3"
    return (
        f"background-color:{bg};color:{color};font-family:Arial,Helvetica,sans-serif;"
        f"font-size:{size};font-weight:{weight};font-style:{slant};"
        f"padding:{padding};border:1px solid {COLOR_BORDER};vertical-align:top;"
        f"line-height:{line_height};"
    )


def _is_category_label(text: str) -> bool:
    plain = re.sub(r"<[^>]+>", "", text).strip().upper()
    if re.match(r"^\d{2}_", plain):
        return False
    plain = re.sub(r"[^A-Z\s&]", "", plain).strip()
    if plain in CATEGORY_NAMES:
        return True
    if plain.startswith("STORY") or plain.startswith("POOL"):
        return True
    return False


def _is_instruction_box_table(table_html: str) -> bool:
    plain = re.sub(r"<[^>]+>", "", table_html).upper()
    return (
        "MUST READ" in plain
        or "INSTRUCTIONS FOR THE CLIENT" in plain
        or "HOW TO SUBMIT" in plain
        or "YOUR UPLOAD FOLDER TREE" in plain
    )


def _is_folder_structure_table(table_html: str) -> bool:
    plain = re.sub(r"<[^>]+>", "", table_html)
    return (
        "Your upload folder tree" in plain
        or "B-Roll Upload" in plain
        or ("├──" in plain and "Section A" in plain)
    )


def _white_inner_tags(inner: str) -> str:
    """Force white text on nested tags inside black box cells."""
    inner = re.sub(
        r"<strong(?![^>]*style=)",
        '<strong style="color:#FFFFFF;font-weight:bold;"',
        inner,
        flags=re.IGNORECASE,
    )
    inner = re.sub(
        r"<em(?![^>]*style=)",
        '<em style="color:#FFFFFF;font-style:italic;"',
        inner,
        flags=re.IGNORECASE,
    )
    return inner


def style_brief_html_tables(html: str) -> str:
    """Apply reference .docx table colors via inline styles (survives Word/GDocs paste)."""
    if not html or "<table" not in html:
        return html

    def style_table(table_html: str) -> str:
        rows = re.findall(r"<tr[^>]*>.*?</tr>", table_html, re.DOTALL | re.IGNORECASE)
        if not rows:
            return table_html

        instruction_box = _is_instruction_box_table(table_html)
        folder_table = _is_folder_structure_table(table_html)
        front_matter_table = instruction_box or folder_table
        styled_rows = []
        data_row_index = 0
        is_video_options_table = False
        is_photo_v2_table = False
        for row in rows:
            if re.search(r"<th\b", row, re.IGNORECASE):
                header_text = re.sub(r"<[^>]+>", "", row).lower()
                is_video_options_table = "quick option" in header_text
                is_photo_v2_table = "good to have" in header_text and "photo" in header_text
                def repl_th(m):
                    inner = _white_inner_tags(m.group(1))
                    return (
                        f'<th style="{_cell_style(COLOR_HEADER, bold=True, color=COLOR_HEADER_TEXT, front_matter=front_matter_table)}">'
                        f"{inner}</th>"
                    )
                styled_rows.append(re.sub(r"<th[^>]*>(.*?)</th>", repl_th, row, flags=re.DOTALL | re.IGNORECASE))
                continue

            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.DOTALL | re.IGNORECASE)
            if not cells:
                styled_rows.append(row)
                continue

            first_text = re.sub(r"<[^>]+>", "", cells[0]).strip()
            if _is_category_label(first_text):
                cat_color = COLOR_CATEGORY_B
                if "CHILDHOOD" in first_text.upper():
                    cat_color = COLOR_CATEGORY_A
                elif any(x in first_text.upper() for x in ("CAREER", "FAMILY", "IMPACT")):
                    cat_color = COLOR_CATEGORY_C
                elif "INSTRUCTIONS" in first_text.upper():
                    cat_color = COLOR_HEADER
                styled_rows.append(
                    f'<tr><td colspan="{len(cells)}" '
                    f'style="{_cell_style(COLOR_HEADER, bold=True, color=COLOR_HEADER_TEXT)}">'
                    f"{_white_inner_tags(cells[0])}</td></tr>"
                )
                continue

            col_styles = []
            ncols = len(cells)
            for ci in range(ncols):
                if front_matter_table:
                    col_styles.append(
                        _cell_style(COLOR_HEADER, bold=True, color=COLOR_HEADER_TEXT, front_matter=True)
                    )
                elif ci == 0 and is_photo_v2_table:
                    col_styles.append(_cell_style("#FFFFFF", bold=True))
                elif ci == 0:
                    col_styles.append(_cell_style(COLOR_ROW_NUM, bold=True))
                elif is_video_options_table and ncols == 4 and ci == 2:
                    col_styles.append(_cell_style(COLOR_QUICK_COL))
                elif is_video_options_table and ncols == 4 and ci == 3:
                    col_styles.append(_cell_style(COLOR_PRO_COL))
                elif data_row_index % 2 == 1:
                    col_styles.append(_cell_style(COLOR_ROW_ALT))
                else:
                    col_styles.append(_cell_style("#FFFFFF"))

            cell_idx = 0

            def repl_td(m):
                nonlocal cell_idx
                style = col_styles[cell_idx] if cell_idx < len(col_styles) else col_styles[-1]
                cell_idx += 1
                inner = m.group(1)
                if front_matter_table:
                    inner = _white_inner_tags(inner)
                return f'<td style="{style}">{inner}</td>'

            styled_rows.append(
                re.sub(r"<td[^>]*>(.*?)</td>", repl_td, row, flags=re.DOTALL | re.IGNORECASE)
            )
            data_row_index += 1

        table_class = "brief-table brief-table-compact" if front_matter_table else "brief-table"
        inner = "".join(styled_rows)
        return (
            f'<table class="{table_class}" cellpadding="0" cellspacing="0" '
            f'style="width:100%;border-collapse:collapse;margin:{TABLE_MARGIN};'
            f'font-family:Arial,Helvetica,sans-serif;font-size:{TABLE_FONT_SIZE_COMPACT if front_matter_table else TABLE_FONT_SIZE};">'
            f"{inner}</table>"
        )

    return re.sub(r"<table[^>]*>.*?</table>", lambda m: style_table(m.group(0)), html, flags=re.DOTALL | re.IGNORECASE)


def md_to_brief_fragment(brief_md: str) -> str:
    """Markdown to HTML fragment with brief styling."""
    extensions = ["tables", "fenced_code", "nl2br", "sane_lists"]
    html = markdown.markdown(brief_md or "", extensions=extensions)
    html = re.sub(
        r"<strong>From your episode:</strong>",
        '<strong class="transcript-label">From your episode:</strong>',
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(r"📌\s*", "", html)
    html = re.sub(
        r"<h1>\s*PAGE\s*1\s*[—–-]\s*",
        "<h1>",
        html,
        flags=re.IGNORECASE,
    )
    html = style_brief_html_tables(html)
    html = _apply_smart_page_breaks(html, brief_md)
    return _polish_brief_html(html)


def _polish_brief_html(html: str) -> str:
    """Tighter spacing, closing block styling, fewer redundant rules."""
    html = re.sub(r"(<hr\s*/>\s*){2,}", "<hr />", html, flags=re.IGNORECASE)
    html = re.sub(r"</table>\s*<hr\s*/>\s*(?=<h2)", "</table>\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<hr\s*/>\s*(?=<h2)", "", html, flags=re.IGNORECASE)
    closing_td = (
        'style="background-color:#f5f0e6;color:#1a1a1a;font-style:italic;'
        "padding:8pt 12pt;font-family:Arial,Helvetica,sans-serif;font-size:10pt;"
        'vertical-align:top;line-height:1.35;border-left:4px solid #c8a84e;"'
    )
    html = re.sub(
        r'(<h2[^>]*>SECTION:\s*CLOSING[^<]*</h2>\s*)'
        r'((?:<table class="brief-table"[^>]*>.*?</table>)|(?:<p[^>]*>.*?</p>))',
        rf'<div class="brief-closing">\1'
        rf'<table class="brief-table" cellpadding="0" cellspacing="0" '
        rf'style="width:100%;border-collapse:collapse;margin:6px 0;">'
        rf"<tr><td {closing_td}>\2</td></tr></table></div>",
        html,
        count=1,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html = re.sub(
        r'(<div class="closing-message-box">\s*<p[^>]*>)\s*\|\s*',
        r"\1",
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r"\s*\|\s*(</p>\s*</div>\s*</div>)",
        r"\1",
        html,
        count=1,
        flags=re.IGNORECASE,
    )
    return html


BRIEF_DOCUMENT_CSS = """
body {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 10pt;
    line-height: 1.25;
    color: #1a1a1a;
    max-width: 8in;
    margin: 0 auto;
    padding: 8px 14px 16px;
    background: #ffffff;
}
.doc-header {
    text-align: center;
    margin-bottom: 4px;
    padding-bottom: 4px;
    border-bottom: 2px solid #000000;
}
.doc-header .doc-logo {
    width: 64px;
    height: 45px;
    max-width: 64px;
    max-height: 45px;
    margin: 0 auto 2px;
    display: block;
    object-fit: contain;
}
.doc-header h1 {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 10pt;
    color: #000000;
    margin: 0 0 2px;
    letter-spacing: 0.3px;
    text-transform: uppercase;
    font-weight: bold;
}
.doc-header .subtitle {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 9.5pt;
    color: #333;
    margin: 0;
    font-weight: 600;
}
.brief-content {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 10pt;
    color: #1a1a1a;
}
.brief-content h1 {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 11pt;
    color: #000000;
    font-weight: bold;
    margin: 8px 0 3px;
}
.page-break + h1,
.page-break + h2 {
    margin-top: 4px;
}
.brief-content h2 {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 9.5pt;
    color: #000000;
    font-weight: bold;
    margin: 4px 0 2px;
}
.brief-content h2.folder-structure-heading,
.brief-content h2.submit-heading {
    margin: 3px 0 1px;
}
.brief-content h3 {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 9.5pt;
    color: #1a1a1a;
    font-weight: bold;
    margin: 8px 0 4px;
}
.brief-content p {
    font-family: Arial, Helvetica, sans-serif;
    margin: 0 0 3px;
    line-height: 1.25;
}
.brief-content em {
    color: #555555;
    font-style: italic;
}
.brief-content strong {
    font-weight: bold;
    color: #1a1a1a;
}
.brief-table th,
.brief-table th strong,
.brief-table th em {
    color: #FFFFFF !important;
}
.brief-table td[style*="background-color:#000000"] strong,
.brief-table td[style*="background-color:#000000"] em {
    color: #FFFFFF !important;
}
.brief-table-compact {
    margin: 2px 0 4px !important;
}
.brief-content hr {
    border: none;
    border-top: 1px solid #e0ddd5;
    margin: 10px 0;
}
.brief-content table.brief-table {
    width: 100%;
    border-collapse: collapse;
    margin: 5px 0;
}
.brief-closing {
    margin: 12px 0 6px;
    page-break-inside: avoid;
}
.brief-closing h2 {
    margin: 0 0 6px;
    color: #000000;
}
.closing-message-box {
    background: #f5f0e6;
    border-left: 4px solid #c8a84e;
    padding: 12px 16px;
}
.closing-message-box p {
    margin: 0;
    line-height: 1.4;
    font-size: 10pt;
    color: #1a1a1a;
}
.closing-message-box em {
    color: #1a1a1a;
    font-style: italic;
}
.closing-message-box strong {
    font-weight: bold;
}
.page-break {
    page-break-before: always;
    break-before: page;
}
"""


def load_logo_base64() -> str | None:
    """Load ISTV logo from static/ for embedding in brief HTML."""
    import base64

    base_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(base_dir, "static")
    for filename in ("logo.png", "logo.svg"):
        path = os.path.join(static_dir, filename)
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as f:
            data = f.read()
        if filename.endswith(".svg"):
            encoded = base64.b64encode(data).decode("ascii")
            return f"data:image/svg+xml;base64,{encoded}"
        return base64.b64encode(data).decode("ascii")
    return None


def build_client_brief_html(
    brief_md: str,
    client_full_name: str,
    episode_title: str,
    logo_b64: str | None = None,
    logo_href: str | None = None,
    generation_date: str | None = None,
    photos_format: str = "v2",
    skip_sanitize: bool = False,
) -> str:
    """Full HTML document matching reference brief layout (no reference-image section)."""
    if skip_sanitize:
        clean_md = brief_md
    elif photos_format == "v2":
        clean_md = sanitize_brief_markdown_v2(brief_md)
    else:
        clean_md = sanitize_brief_markdown(brief_md)
    clean_md = _ensure_client_front_matter(clean_md, client_full_name)
    brief_html = md_to_brief_fragment(clean_md)

    logo_img = ""
    logo_attrs = (
        f'class="doc-logo" width="{LOGO_HTML_WIDTH}" height="{LOGO_HTML_HEIGHT}" '
        f'style="width:{LOGO_HTML_WIDTH}px;height:{LOGO_HTML_HEIGHT}px;"'
    )
    logo_src: str | None = None
    if logo_href:
        logo_src = logo_href
    else:
        static_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "logo.png")
        if os.path.isfile(static_png):
            logo_src = Path(static_png).as_uri()
        else:
            logo_data = logo_b64 or load_logo_base64()
            if logo_data:
                logo_src = (
                    logo_data
                    if logo_data.startswith("data:")
                    else f"data:image/png;base64,{logo_data}"
                )
    if logo_src:
        logo_img = f'<img src="{logo_src}" alt="Inside Success" {logo_attrs} />'

    return f"""<!DOCTYPE html>
<html lang="en" xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:w="urn:schemas-microsoft-com:office:word">
<head>
    <meta charset="UTF-8">
    <meta name="ProgId" content="Word.Document">
    <meta name="Generator" content="ISTV B-Roll Brief">
    <!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View></w:WordDocument></xml><![endif]-->
    <title>{client_full_name} - Post-Edit B-Roll and Production Brief</title>
    <style>{BRIEF_DOCUMENT_CSS}</style>
</head>
<body>
    <div class="doc-header">
        {logo_img}
        <h1>Post-Edit B-Roll and Production Brief</h1>
        <p class="subtitle">{client_full_name} - {episode_title}</p>
    </div>
    <div class="brief-content">
        {brief_html}
    </div>
</body>
</html>"""


def build_production_brief(
    brief_md: str,
    client_full_name: str,
    episode_title: str,
    logo_b64: str | None = None,
    logo_href: str | None = None,
) -> tuple[str, str]:
    """
    Sanitized markdown + full HTML document (updated-7 layout: v2 tables,
    smart page breaks, no generated date, Word-ready styling).
    """
    clean_md = sanitize_brief_markdown_v2(brief_md)
    clean_md = _ensure_client_front_matter(clean_md, client_full_name)
    html = build_client_brief_html(
        clean_md,
        client_full_name,
        episode_title,
        logo_b64=logo_b64,
        logo_href=logo_href,
        photos_format="v2",
        skip_sanitize=True,
    )
    return clean_md, html


def export_production_brief_docx(
    html_path: str | os.PathLike,
    docx_path: str | os.PathLike,
    brief_md_path: str | os.PathLike | None = None,
) -> bool:
    """Convert production brief HTML to .docx with Word COM post-processing."""
    import subprocess
    import sys

    base_dir = os.path.dirname(os.path.abspath(__file__))
    cmd = [
        sys.executable,
        os.path.join(base_dir, "html_to_docx.py"),
        str(html_path),
        "-o",
        str(docx_path),
    ]
    if brief_md_path and os.path.isfile(brief_md_path):
        cmd.extend(["--brief-md", str(brief_md_path)])
    result = subprocess.run(cmd, check=False)
    return result.returncode == 0 and os.path.isfile(docx_path)
