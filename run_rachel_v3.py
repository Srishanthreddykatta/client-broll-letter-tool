"""
Fresh end-to-end generation for Rachel Fino using the two-page prompt v3.
Outputs Google Docs / Word-friendly HTML and .docx (Arial, reference table colors).
No separate Visual Reference Images section.
"""

import os
import sys
import time
import re
import subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.insert(0, os.path.dirname(__file__))

import anthropic
from app import (
    CLAUDE_MODEL,
    CLAUDE_MAX_TOKENS,
    CLAUDE_TIMEOUT_SECONDS,
)
from brief_document import build_production_brief, export_production_brief_docx

BASE_DIR = os.path.dirname(__file__)
CUT_SHEET_PATH = os.path.join(
    BASE_DIR, "input", "2026-05-23_qroot_1", "spreadsheets",
    "rachel_fidino_16-20_mins_spreadsheet_claude_raw.txt",
)
PROMPT_PATH = os.path.join(BASE_DIR, "prompt_v2.txt")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "Rachel_v3_two_page")
EXISTING_MD = os.path.join(OUTPUT_DIR, "Rachel_Fino_BRoll_Brief_v3.md")

CLIENT_FIRST_NAME = "Rachel"
CLIENT_FULL_NAME = "Rachel Fino"
EPISODE_TITLE = "The Woman Who Kept Getting Back Up"
INDUSTRY = "Women's Health / Medical Aesthetics"
DEADLINE = "TBD"
EDITOR_NOTES = "None provided."


def write_outputs(brief_md: str) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    clean_md, html_output = build_production_brief(
        brief_md, CLIENT_FULL_NAME, EPISODE_TITLE
    )

    md_path = os.path.join(OUTPUT_DIR, "Rachel_Fino_BRoll_Brief_v3.md")
    html_path = os.path.join(OUTPUT_DIR, "Rachel_Fino_BRoll_Brief_v3.html")
    docx_path = os.path.join(OUTPUT_DIR, "Rachel_Fino_BRoll_Brief_v3.docx")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(clean_md)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_output)

    print("\nConverting to .docx...")
    export_production_brief_docx(html_path, docx_path, md_path)

    print(f"\n{'=' * 60}")
    print("DONE!")
    print(f"{'=' * 60}")
    print(f"\nOutput: {OUTPUT_DIR}")
    print(f"  Rachel_Fino_BRoll_Brief_v3.html  ({os.path.getsize(html_path) / 1024:.0f} KB)")
    print(f"  Rachel_Fino_BRoll_Brief_v3.md    ({len(clean_md):,} chars)")
    if os.path.isfile(docx_path):
        print(f"  Rachel_Fino_BRoll_Brief_v3.docx  ({os.path.getsize(docx_path) / 1024:.0f} KB)")
    print("\nOpen the .html in browser, or use the .docx directly.")


def generate_brief_from_cut_sheet() -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    prompt_text = prompt_template.replace("{client_first_name}", CLIENT_FIRST_NAME)
    prompt_text = prompt_text.replace("{client_full_name}", CLIENT_FULL_NAME)
    prompt_text = prompt_text.replace("{episode_title}", EPISODE_TITLE)
    prompt_text = prompt_text.replace("{industry}", INDUSTRY)
    prompt_text = prompt_text.replace("{deadline}", DEADLINE)
    prompt_text = prompt_text.replace("{editor_notes}", EDITOR_NOTES)

    with open(CUT_SHEET_PATH, "r", encoding="utf-8") as f:
        cut_sheet_text = f.read()

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(
        api_key=api_key, timeout=CLAUDE_TIMEOUT_SECONDS, max_retries=0
    )
    full_message = (
        f"{prompt_text}\n\n---\n\n## CUT SHEET CONTENT\n\n"
        f"```\n{cut_sheet_text}\n```"
    )

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=CLAUDE_MAX_TOKENS,
        temperature=0.4,
        messages=[{"role": "user", "content": [{"type": "text", "text": full_message}]}],
    )

    brief_md = ""
    for block in message.content:
        if getattr(block, "type", None) == "text":
            brief_md += block.text
    return brief_md


def main():
    print("=" * 60)
    print("RACHEL FINO - Two-Page B-Roll Brief (reference layout)")
    print("=" * 60)
    print(f"\nClient: {CLIENT_FULL_NAME}")
    print(f"Episode: {EPISODE_TITLE}\n")

    use_existing = "--regenerate" not in sys.argv and os.path.isfile(EXISTING_MD)

    if use_existing:
        print("[1/2] Using existing markdown (pass --regenerate to call Claude)...")
        with open(EXISTING_MD, "r", encoding="utf-8") as f:
            brief_md = f.read()
    else:
        print("[1/2] Loading prompt and cut sheet...")
        print("[2/2] Generating brief via Claude...")
        start = time.time()
        brief_md = generate_brief_from_cut_sheet()
        print(f"  Generated in {time.time() - start:.1f}s ({len(brief_md):,} characters)")

    print("\nBuilding styled HTML and .docx...")
    write_outputs(brief_md)


if __name__ == "__main__":
    main()
