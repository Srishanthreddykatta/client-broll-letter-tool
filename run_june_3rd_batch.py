"""
Generate v2 B-Roll letters (updated-7 layout) from cut sheets in input/june 3rd/.
Outputs .md, .html, and .docx to output/june 3rd/.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.insert(0, os.path.dirname(__file__))

import anthropic
from app import CLAUDE_MODEL, CLAUDE_MAX_TOKENS, CLAUDE_TIMEOUT_SECONDS
from brief_document import build_production_brief, export_production_brief_docx

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input" / "june 3rd"
OUTPUT_DIR = BASE_DIR / "output" / "june 3rd"
PROMPT_PATH = BASE_DIR / "prompt_v2.txt"

INDUSTRY = "[Extract from cut sheet]"
DEADLINE = "TBD"
EDITOR_NOTES = "None provided."


def _safe_filename(name: str) -> str:
    safe = re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "_")
    return safe or "Client"


def _extract_from_cut_sheet(cut_sheet_text: str) -> tuple[str, str, str]:
    """Return (first_name, full_name, episode_title) from cut_sheet banner_title."""
    match = re.search(
        r'"id":\s*"cut_sheet"[\s\S]*?"banner_title":\s*"([^"]+)"',
        cut_sheet_text,
        re.IGNORECASE,
    )
    if not match:
        match = re.search(r'"banner_title":\s*"([^"]+)"', cut_sheet_text)
    banner = (match.group(1) if match else "").strip()
    if not banner or banner.upper().startswith("APPENDIX"):
        raise ValueError("Could not find cut_sheet banner_title")

    if " — " in banner:
        full_name, episode_title = banner.split(" — ", 1)
    elif " - " in banner:
        full_name, episode_title = banner.split(" - ", 1)
    else:
        full_name, episode_title = banner, "Episode"

    full_name = full_name.strip()
    episode_title = episode_title.strip()
    first_name = full_name.split()[0] if full_name else "Client"
    return first_name, full_name, episode_title


def _build_prompt(
    first_name: str, full_name: str, episode_title: str
) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    text = template.replace("{client_first_name}", first_name)
    text = text.replace("{client_full_name}", full_name)
    text = text.replace("{episode_title}", episode_title)
    text = text.replace("{industry}", INDUSTRY)
    text = text.replace("{deadline}", DEADLINE)
    text = text.replace("{editor_notes}", EDITOR_NOTES)
    return text


def _call_claude(prompt_text: str, cut_sheet_text: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in .env")

    client = anthropic.Anthropic(
        api_key=api_key, timeout=CLAUDE_TIMEOUT_SECONDS, max_retries=2
    )
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=CLAUDE_MAX_TOKENS,
        temperature=0.4,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"{prompt_text}\n\n---\n\n## CUT SHEET CONTENT\n\n"
                            f"```\n{cut_sheet_text}\n```"
                        ),
                    }
                ],
            }
        ],
    )
    brief_md = ""
    for block in message.content:
        if getattr(block, "type", None) == "text":
            brief_md += block.text
    if not brief_md.strip():
        raise RuntimeError("Claude returned empty brief")
    return brief_md


def _export_client(
    base_name: str,
    full_name: str,
    episode_title: str,
    brief_md: str,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    v2_md, html = build_production_brief(brief_md, full_name, episode_title)

    md_path = OUTPUT_DIR / f"{base_name}_BRoll_Brief_v2.md"
    html_path = OUTPUT_DIR / f"{base_name}_BRoll_Brief_v2.html"
    docx_path = OUTPUT_DIR / f"{base_name}_BRoll_Brief_v2.docx"

    md_path.write_text(v2_md, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    export_production_brief_docx(html_path, docx_path, md_path)


def main() -> None:
    if not INPUT_DIR.is_dir():
        print(f"Missing input folder: {INPUT_DIR}")
        sys.exit(1)

    cut_files = sorted(INPUT_DIR.glob("*_spreadsheet_claude_raw.txt"))
    if not cut_files:
        print(f"No cut sheets in {INPUT_DIR}")
        sys.exit(1)

    print("=" * 60)
    print("June 3rd batch — B-Roll letters (v2 layout)")
    print("=" * 60)
    print(f"Input:  {INPUT_DIR}")
    print(f"Output: {OUTPUT_DIR}\n")

    ok, fail = 0, 0
    for path in cut_files:
        print(f"\n--- {path.name} ---")
        try:
            cut_text = path.read_text(encoding="utf-8")
            first_name, full_name, episode_title = _extract_from_cut_sheet(cut_text)
            print(f"  Client:  {full_name}")
            print(f"  Episode: {episode_title}")

            prompt = _build_prompt(first_name, full_name, episode_title)
            t0 = time.time()
            print("  Calling Claude...")
            brief_md = _call_claude(prompt, cut_text)
            print(f"  Brief: {len(brief_md):,} chars in {time.time() - t0:.1f}s")

            base = _safe_filename(full_name)
            _export_client(base, full_name, episode_title, brief_md)
            print(f"  Saved: {base}_BRoll_Brief_v2.{{md,html,docx}}")
            ok += 1
        except Exception as exc:
            print(f"  FAILED: {exc}")
            fail += 1

    print(f"\n{'=' * 60}")
    print(f"Done: {ok} succeeded, {fail} failed")
    print(f"Output folder: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
