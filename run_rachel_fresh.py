"""
Fresh end-to-end generation for Rachel Fino using the updated prompt_v2.
Takes the cut sheet → generates brief via Claude → generates images via Gemini → outputs HTML.
"""

import os
import sys
import time
import base64
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.insert(0, os.path.dirname(__file__))

import anthropic
from app import (
    build_enriched_brief_html,
    generate_location_images,
    save_images_to_disk,
    get_gemini_api_key,
    get_logo_base64,
    GEMINI_AVAILABLE,
    CLAUDE_MODEL,
    CLAUDE_MAX_TOKENS,
    CLAUDE_TIMEOUT_SECONDS,
)

BASE_DIR = os.path.dirname(__file__)
CUT_SHEET_PATH = os.path.join(BASE_DIR, "input", "2026-05-23_qroot_1", "spreadsheets", "rachel_fidino_16-20_mins_spreadsheet_claude_raw.txt")
PROMPT_PATH = os.path.join(BASE_DIR, "prompt_v2.txt")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "Rachel_old_vs_new")

CLIENT_FIRST_NAME = "Rachel"
CLIENT_FULL_NAME = "Rachel Fino"
EPISODE_TITLE = "The Woman Who Kept Getting Back Up"
INDUSTRY = "Women's Health / Medical Aesthetics"
DEADLINE = "TBD"
EDITOR_NOTES = "None provided."


def build_standalone_html(brief_html, client_full_name, episode_title):
    logo_b64 = get_logo_base64()
    today = datetime.now().strftime("%B %d, %Y")
    logo_img = f'<img src="data:image/png;base64,{logo_b64}" alt="Inside Success TV">' if logo_b64 else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{client_full_name} — Post-Edit B-Roll Brief</title>
    <style>
        body {{
            font-family: Arial, Helvetica, sans-serif;
            font-size: 11pt;
            line-height: 1.55;
            color: #1a1a1a;
            max-width: 7.5in;
            margin: 0 auto;
            padding: 24px 32px 48px;
            background: #ffffff;
        }}
        .export-header {{
            text-align: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 2px solid #c8a84e;
        }}
        .export-header img {{ width: 200px; margin-bottom: 10px; }}
        .export-header h1 {{ font-size: 16pt; color: #8a7234; margin: 0 0 6px; letter-spacing: 0.5px; }}
        .export-header .subtitle {{ font-size: 12pt; color: #444; margin: 0; }}
        .export-header .date {{ font-size: 9pt; color: #888; margin-top: 8px; }}
        .brief-content h1 {{ font-size: 14pt; color: #8a7234; margin: 28px 0 10px; padding-top: 8px; }}
        .brief-content h1:first-of-type {{ margin-top: 0; }}
        .brief-content h2 {{ font-size: 12pt; color: #333; margin: 20px 0 8px; }}
        .brief-content h2.major-section-start {{ page-break-before: always; margin-top: 28px; }}
        .brief-content h3 {{ font-size: 11pt; color: #555; margin: 14px 0 6px; }}
        .brief-content p {{ margin: 0 0 8px; }}
        .brief-content ul, .brief-content ol {{ margin: 0 0 12px 22px; }}
        .brief-content li {{ margin-bottom: 6px; }}
        .brief-content strong {{ color: #1a1a1a; }}
        .brief-content em {{ color: #555; }}
        .broll-reference-still {{
            text-align: center;
            margin: 16px 0 20px;
            padding: 12px;
            border: 1px solid #d4c9a8;
            background: #faf8f3;
            border-radius: 6px;
            page-break-inside: avoid;
        }}
        .broll-reference-label {{
            font-size: 9pt; font-weight: bold; color: #8a7234;
            text-transform: uppercase; letter-spacing: 0.5px; margin: 0 0 8px;
        }}
        .broll-reference-still img {{
            width: 600px; max-width: 100%; height: auto;
            border-radius: 4px; display: block; margin: 0 auto;
        }}
        .broll-reference-caption {{
            font-size: 8pt; color: #777; font-style: italic; margin: 8px 0 0;
        }}
        .brief-content hr {{ border: none; border-top: 1px solid #ddd; margin: 16px 0; }}
        .brief-content pre {{
            font-family: Courier, monospace; font-size: 9pt;
            background: #f5f5f0; border: 1px solid #ddd; padding: 10px;
        }}
        .tldr-box {{
            border: 2px solid #c8a84e; background: #fdfbf5;
            padding: 16px 20px; margin-bottom: 24px; border-radius: 6px;
        }}
        .tldr-box h2 {{ font-size: 13pt; color: #8a7234; margin: 0 0 10px; border: none; padding: 0; }}
        .tldr-box p {{ margin-bottom: 5px; font-size: 10.5pt; }}
        details.brief-section {{ margin-bottom: 10px; }}
        details.brief-section summary {{ display: none; }}
        .brief-section-body {{ display: block; }}
    </style>
</head>
<body>
    <div class="export-header">
        {logo_img}
        <h1>POST-EDIT B-ROLL &amp; PRODUCTION BRIEF</h1>
        <p class="subtitle">{client_full_name} — {episode_title}</p>
        <p class="date">Generated {today}</p>
    </div>
    <div class="brief-content">
        {brief_html}
    </div>
</body>
</html>"""


def main():
    print("=" * 60)
    print("RACHEL FINO — Fresh B-Roll Letter (Updated Prompt v2)")
    print("=" * 60)
    print(f"\nClient: {CLIENT_FULL_NAME}")
    print(f"Episode: {EPISODE_TITLE}")
    print(f"Cut Sheet: {os.path.basename(CUT_SHEET_PATH)}")
    print()

    # Step 1: Load prompt
    print("[1/4] Loading prompt_v2.txt...")
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    prompt_text = prompt_template.replace("{client_first_name}", CLIENT_FIRST_NAME)
    prompt_text = prompt_text.replace("{client_full_name}", CLIENT_FULL_NAME)
    prompt_text = prompt_text.replace("{episode_title}", EPISODE_TITLE)
    prompt_text = prompt_text.replace("{industry}", INDUSTRY)
    prompt_text = prompt_text.replace("{deadline}", DEADLINE)
    prompt_text = prompt_text.replace("{editor_notes}", EDITOR_NOTES)
    print(f"  Prompt ready: {len(prompt_text):,} characters")

    # Step 2: Load cut sheet
    print("[2/4] Loading cut sheet...")
    with open(CUT_SHEET_PATH, "r", encoding="utf-8") as f:
        cut_sheet_text = f.read()
    print(f"  Cut sheet: {len(cut_sheet_text):,} characters")

    # Step 3: Generate brief via Claude
    print(f"\n[3/4] Generating brief via Claude ({CLAUDE_MODEL})...")
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in .env")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key, timeout=CLAUDE_TIMEOUT_SECONDS, max_retries=0)

    full_message = (
        f"{prompt_text}\n\n"
        f"---\n\n"
        f"## CUT SHEET CONTENT\n\n"
        f"Below is the full text extracted from the client's cut sheet. "
        f"Use this as your sole source of story information.\n\n"
        f"```\n{cut_sheet_text}\n```"
    )

    start = time.time()
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=CLAUDE_MAX_TOKENS,
        temperature=0.4,
        messages=[{"role": "user", "content": [{"type": "text", "text": full_message}]}],
    )
    elapsed = time.time() - start

    brief_md = ""
    for block in message.content:
        if getattr(block, "type", None) == "text":
            brief_md += block.text

    print(f"  Brief generated in {elapsed:.1f}s ({len(brief_md):,} characters)")

    # Step 4: Generate images via Gemini
    print("\n[4/4] Generating reference images via Gemini...")
    client_images = []
    gemini_key = get_gemini_api_key()

    if gemini_key and gemini_key != "your-gemini-key-here" and GEMINI_AVAILABLE:
        start = time.time()
        try:
            client_images = generate_location_images(gemini_key, brief_md)
            elapsed = time.time() - start
            print(f"  {len(client_images)} images generated in {elapsed:.1f}s")
            if client_images:
                save_images_to_disk(client_images, CLIENT_FULL_NAME)
        except Exception as e:
            print(f"  Image generation error: {e}")
    else:
        print("  Gemini not available, skipping images.")

    # Build HTML
    print("\nBuilding final HTML...")
    enriched_html = build_enriched_brief_html(brief_md, client_images)
    standalone_html = build_standalone_html(enriched_html, CLIENT_FULL_NAME, EPISODE_TITLE)

    # Save everything
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    md_path = os.path.join(OUTPUT_DIR, "NEW_Rachel_BRoll_Brief.md")
    html_path = os.path.join(OUTPUT_DIR, "NEW_Rachel_BRoll_Brief.html")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(brief_md)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(standalone_html)

    print(f"\n{'=' * 60}")
    print("DONE!")
    print(f"{'=' * 60}")
    print(f"\nOutput folder: {OUTPUT_DIR}")
    print(f"  NEW_Rachel_BRoll_Brief.md   ({len(brief_md):,} chars)")
    print(f"  NEW_Rachel_BRoll_Brief.html ({os.path.getsize(html_path) / 1024:.0f} KB, {len(client_images)} images)")
    print(f"\nOpen the .html file in your browser to view.")


if __name__ == "__main__":
    main()
