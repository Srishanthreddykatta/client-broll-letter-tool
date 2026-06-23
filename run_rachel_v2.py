"""
Fresh end-to-end generation for Rachel Fino using the NEW two-page prompt.
Generates: Brief → Images → Google Docs-friendly HTML (paste-ready for reviewers).
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
    generate_location_images,
    save_images_to_disk,
    get_gemini_api_key,
    get_logo_base64,
    extract_locations_for_images,
    build_image_prompt,
    compress_reference_image,
    GEMINI_AVAILABLE,
    CLAUDE_MODEL,
    CLAUDE_MAX_TOKENS,
    CLAUDE_TIMEOUT_SECONDS,
)
import markdown

BASE_DIR = os.path.dirname(__file__)
CUT_SHEET_PATH = os.path.join(BASE_DIR, "input", "2026-05-23_qroot_1", "spreadsheets", "rachel_fidino_16-20_mins_spreadsheet_claude_raw.txt")
PROMPT_PATH = os.path.join(BASE_DIR, "prompt_v2.txt")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "Rachel_v2_TwoPage")

CLIENT_FIRST_NAME = "Rachel"
CLIENT_FULL_NAME = "Rachel Fino"
EPISODE_TITLE = "The Woman Who Kept Getting Back Up"
INDUSTRY = "Women's Health / Medical Aesthetics"
DEADLINE = "TBD"
EDITOR_NOTES = "None provided."


def build_gdocs_html(brief_md, images_list, client_full_name, episode_title):
    """
    Build a Google Docs paste-friendly HTML file.
    - Tables render cleanly when copy-pasted into Google Docs
    - Minimal styling that survives paste (inline styles on key elements)
    - Two-page layout with clear visual separation
    - Reference images embedded inline at proper positions
    """
    logo_b64 = get_logo_base64()
    today = datetime.now().strftime("%B %d, %Y")

    # Build image lookup by shot name
    img_lookup = {}
    for img in (images_list or []):
        img_lookup[img['header'].strip().lower()] = img

    # Convert markdown to HTML with table support
    extensions = ["tables", "fenced_code", "nl2br", "sane_lists"]
    body_html = markdown.markdown(brief_md, extensions=extensions)

    # Inject reference images after shot headers in the Visual Reference section
    for img in (images_list or []):
        header = img['header']
        safe_header = re.escape(header)
        # Look for the shot heading pattern and inject image after it
        pattern = rf'(<strong>Shot \d+ — {safe_header}</strong>)'
        replacement = (
            rf'\1'
            rf'<div style="text-align:center;margin:12px 0 16px;padding:10px;'
            rf'border:1px solid #d4c9a8;background:#faf8f3;border-radius:4px;">'
            rf'<img src="data:{img.get("mime","image/jpeg")};base64,{img["b64"]}" '
            rf'style="max-width:560px;width:100%;height:auto;border-radius:3px;" '
            rf'alt="Reference — {header}" />'
            rf'<p style="font-size:8pt;color:#666;font-style:italic;margin:6px 0 0;">'
            rf'Visual reference for videographer — match mood and framing</p></div>'
        )
        body_html = re.sub(pattern, replacement, body_html, flags=re.IGNORECASE)

        # Also try matching [REFERENCE IMAGE: Shot N — Name] placeholders
        placeholder_pattern = rf'\[REFERENCE IMAGE:.*?{safe_header}.*?\]'
        img_block = (
            f'<div style="text-align:center;margin:12px 0 16px;padding:10px;'
            f'border:1px solid #d4c9a8;background:#faf8f3;border-radius:4px;">'
            f'<img src="data:{img.get("mime","image/jpeg")};base64,{img["b64"]}" '
            f'style="max-width:560px;width:100%;height:auto;border-radius:3px;" '
            f'alt="Reference — {header}" />'
            f'<p style="font-size:8pt;color:#666;font-style:italic;margin:6px 0 0;">'
            f'Visual reference for videographer — match mood and framing</p></div>'
        )
        body_html = re.sub(placeholder_pattern, img_block, body_html, flags=re.IGNORECASE)

    logo_img = ""
    if logo_b64:
        logo_img = f'<img src="data:image/png;base64,{logo_b64}" style="width:180px;margin-bottom:8px;" alt="Inside Success TV">'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{client_full_name} — Post-Edit B-Roll & Production Brief</title>
    <style>
        body {{
            font-family: Arial, Helvetica, sans-serif;
            font-size: 10.5pt;
            line-height: 1.5;
            color: #1a1a1a;
            max-width: 8in;
            margin: 0 auto;
            padding: 20px 28px 40px;
            background: #fff;
        }}

        /* Header */
        .doc-header {{
            text-align: center;
            padding-bottom: 14px;
            margin-bottom: 20px;
            border-bottom: 2px solid #c8a84e;
        }}
        .doc-header h1 {{
            font-size: 14pt;
            color: #7a6428;
            margin: 0 0 4px;
            letter-spacing: 0.3px;
        }}
        .doc-header .subtitle {{
            font-size: 11pt;
            color: #444;
            margin: 0;
        }}
        .doc-header .date {{
            font-size: 8.5pt;
            color: #999;
            margin-top: 6px;
        }}

        /* Page separator */
        .page-break {{
            page-break-before: always;
            border-top: 3px solid #c8a84e;
            margin: 32px 0 24px;
            padding-top: 20px;
        }}

        /* Tables — clean, minimal, Google Docs friendly */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0 18px;
            font-size: 10pt;
        }}
        th {{
            background: #f7f4ec;
            color: #5a4a1e;
            font-weight: bold;
            text-align: left;
            padding: 8px 10px;
            border: 1px solid #d4c9a8;
            font-size: 9.5pt;
        }}
        td {{
            padding: 7px 10px;
            border: 1px solid #e0ddd5;
            vertical-align: top;
        }}
        tr:nth-child(even) td {{
            background: #fdfcf9;
        }}

        /* Section headers */
        h1 {{
            font-size: 13pt;
            color: #7a6428;
            margin: 24px 0 8px;
            padding-bottom: 4px;
            border-bottom: 1px solid #e8e2d0;
        }}
        h2 {{
            font-size: 11.5pt;
            color: #333;
            margin: 18px 0 8px;
        }}
        h3 {{
            font-size: 10.5pt;
            color: #555;
            margin: 12px 0 6px;
        }}

        /* Content */
        p {{ margin: 0 0 8px; }}
        ul, ol {{ margin: 0 0 10px 20px; }}
        li {{ margin-bottom: 4px; }}
        strong {{ color: #1a1a1a; }}
        em {{ color: #555; }}
        hr {{
            border: none;
            border-top: 1px solid #e0ddd5;
            margin: 14px 0;
        }}
        blockquote {{
            margin: 8px 0;
            padding: 6px 14px;
            border-left: 3px solid #c8a84e;
            background: #fdfbf5;
            font-style: italic;
            color: #555;
        }}

        /* Submission footer box */
        .submit-box {{
            border: 2px solid #c8a84e;
            background: #fdfbf5;
            padding: 12px 16px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .submit-box strong {{
            color: #7a6428;
        }}

        /* Closing box */
        .closing-box {{
            border: 2px solid #c8a84e;
            background: #fdfbf5;
            padding: 14px 18px;
            margin: 24px 0 0;
            border-radius: 4px;
            text-align: center;
        }}

        /* Reference images */
        .ref-image {{
            text-align: center;
            margin: 12px 0 16px;
            padding: 10px;
            border: 1px solid #d4c9a8;
            background: #faf8f3;
            border-radius: 4px;
        }}
        .ref-image img {{
            max-width: 560px;
            width: 100%;
            height: auto;
            border-radius: 3px;
        }}
        .ref-image .caption {{
            font-size: 8pt;
            color: #666;
            font-style: italic;
            margin: 6px 0 0;
        }}

        /* Print / paste helpers */
        @media print {{
            .page-break {{ page-break-before: always; }}
            body {{ padding: 0; }}
        }}
    </style>
</head>
<body>
    <div class="doc-header">
        {logo_img}
        <h1>POST-EDIT B-ROLL & PRODUCTION BRIEF</h1>
        <p class="subtitle">{client_full_name} — {episode_title}</p>
        <p class="date">Generated {today}</p>
    </div>

    <div class="brief-body">
        {body_html}
    </div>
</body>
</html>"""

    return html


def main():
    print("=" * 60)
    print("RACHEL FINO — Fresh B-Roll Letter (v2 Two-Page Format)")
    print("=" * 60)
    print(f"\nClient: {CLIENT_FULL_NAME}")
    print(f"Episode: {EPISODE_TITLE}")
    print(f"Output: {OUTPUT_DIR}")
    print()

    # Step 1: Load prompt
    print("[1/4] Loading updated prompt_v2.txt...")
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    prompt_text = prompt_template.replace("{client_first_name}", CLIENT_FIRST_NAME)
    prompt_text = prompt_text.replace("{client_full_name}", CLIENT_FULL_NAME)
    prompt_text = prompt_text.replace("{episode_title}", EPISODE_TITLE)
    prompt_text = prompt_text.replace("{industry}", INDUSTRY)
    prompt_text = prompt_text.replace("{deadline}", DEADLINE)
    prompt_text = prompt_text.replace("{editor_notes}", EDITOR_NOTES)
    print(f"  Prompt: {len(prompt_text):,} characters")

    # Step 2: Load cut sheet
    print("[2/4] Loading Rachel's cut sheet...")
    with open(CUT_SHEET_PATH, "r", encoding="utf-8") as f:
        cut_sheet_text = f.read()
    print(f"  Cut sheet: {len(cut_sheet_text):,} characters")

    # Step 3: Generate brief via Claude
    print(f"\n[3/4] Generating two-page brief via Claude ({CLAUDE_MODEL})...")
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
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

    print(f"  Generated in {elapsed:.1f}s ({len(brief_md):,} characters)")

    # Step 4: Generate reference images
    print("\n[4/4] Generating reference images via Gemini...")
    client_images = []
    gemini_key = get_gemini_api_key()

    if gemini_key and gemini_key != "your-gemini-key-here" and GEMINI_AVAILABLE:
        start = time.time()
        try:
            # Extract shot names from [REFERENCE IMAGE: Shot N — Name] placeholders
            shot_matches = re.findall(r'\[REFERENCE IMAGE:\s*Shot\s*\d+\s*(?:—|-)\s*(.+?)\]', brief_md)
            if not shot_matches:
                # Fallback: try table format "**Shot Name** *duration*"
                shot_matches = re.findall(r'\*\*(\w[\w\s/]+?)\*\*\s*\*\d+', brief_md)

            from concurrent.futures import ThreadPoolExecutor, as_completed
            from google import genai
            from google.genai import types as genai_types

            genai_client = genai.Client(api_key=gemini_key)

            def _gen_one(shot_name):
                prompt = build_image_prompt(shot_name, f"Documentary B-roll shot for {CLIENT_FULL_NAME}, {INDUSTRY}", lifestyle_pool=False)
                try:
                    response = genai_client.models.generate_content(
                        model="gemini-2.5-flash-image",
                        contents=[prompt],
                        config=genai_types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
                    )
                    if response.candidates and response.candidates[0].content:
                        for part in response.candidates[0].content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                img_bytes = part.inline_data.data
                                mime = getattr(part.inline_data, 'mime_type', 'image/png') or 'image/png'
                                b64 = base64.b64encode(img_bytes).decode('utf-8')
                                b64, mime = compress_reference_image(b64, mime)
                                return {'header': shot_name, 'b64': b64, 'mime': mime, 'width': 560}
                except Exception as e:
                    print(f"    Image failed for '{shot_name}': {e}")
                return None

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(_gen_one, name) for name in shot_matches]
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        client_images.append(result)

            elapsed = time.time() - start
            print(f"  {len(client_images)} images in {elapsed:.1f}s")
            if client_images:
                img_folder = os.path.join(OUTPUT_DIR, "images")
                os.makedirs(img_folder, exist_ok=True)
                for img in client_images:
                    header = img['header']
                    safe_h = re.sub(r'[^\w\s-]', '', header).strip().replace(' ', '_')
                    mime = img.get('mime', 'image/png')
                    ext = 'png' if 'png' in mime else 'jpeg'
                    fpath = os.path.join(img_folder, f"{safe_h}.{ext}")
                    with open(fpath, 'wb') as f:
                        f.write(base64.b64decode(img['b64']))
                print(f"  Saved to: {img_folder}")
        except Exception as e:
            print(f"  Image error: {e}")
    else:
        print("  Gemini not available, using placeholders.")

    # Build outputs
    print("\nBuilding final outputs...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Save markdown
    md_path = os.path.join(OUTPUT_DIR, "Rachel_Fino_BRoll_Brief_v2.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(brief_md)

    # Build Google Docs-friendly HTML
    html_content = build_gdocs_html(brief_md, client_images, CLIENT_FULL_NAME, EPISODE_TITLE)
    html_path = os.path.join(OUTPUT_DIR, "Rachel_Fino_BRoll_Brief_v2.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n{'=' * 60}")
    print("DONE!")
    print(f"{'=' * 60}")
    print(f"\nOutput: {OUTPUT_DIR}")
    print(f"  Rachel_Fino_BRoll_Brief_v2.md    ({len(brief_md):,} chars)")
    print(f"  Rachel_Fino_BRoll_Brief_v2.html  ({os.path.getsize(html_path)/1024:.0f} KB)")
    if client_images:
        print(f"  images/  ({len(client_images)} reference stills)")
    print(f"\nTo use: Open .html in browser > Ctrl+A > Ctrl+C > Paste into Google Docs")


if __name__ == "__main__":
    main()
