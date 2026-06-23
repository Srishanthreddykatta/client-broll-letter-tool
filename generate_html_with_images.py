"""
Generate a full HTML B-Roll letter with reference images for Rachel
using the updated prompt_v2.txt, matching the app's normal output.
"""

import os
import sys
import time
import shutil
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.insert(0, os.path.dirname(__file__))

from app import (
    build_enriched_brief_html,
    generate_location_images,
    save_images_to_disk,
    get_gemini_api_key,
    get_logo_base64,
    md_to_html,
    GEMINI_AVAILABLE,
)

BASE_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "Rachel_old_vs_new")

CLIENT_FULL_NAME = "Rachel Fino"
EPISODE_TITLE = "The Woman Who Kept Getting Back Up"


def build_standalone_html(brief_html, client_full_name, episode_title, brief_type="client"):
    """Build the same standalone HTML the app generates for download."""
    logo_b64 = get_logo_base64()
    today = datetime.now().strftime("%B %d, %Y")

    logo_img = ""
    if logo_b64:
        logo_img = f'<img src="data:image/png;base64,{logo_b64}" alt="Inside Success TV">'

    if brief_type == "editor":
        title_line = '<h1>EDITOR B-ROLL DECISION SHEET</h1>'
        subtitle_extra = '<p class="subtitle" style="color:#c0392b;font-weight:bold;">Internal Use Only</p>'
    else:
        title_line = '<h1>POST-EDIT B-ROLL &amp; PRODUCTION BRIEF</h1>'
        subtitle_extra = ''

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
        .export-header img {{
            width: 200px;
            margin-bottom: 10px;
        }}
        .export-header h1 {{
            font-size: 16pt;
            color: #8a7234;
            margin: 0 0 6px;
            letter-spacing: 0.5px;
        }}
        .export-header .subtitle {{
            font-size: 12pt;
            color: #444;
            margin: 0;
        }}
        .export-header .date {{
            font-size: 9pt;
            color: #888;
            margin-top: 8px;
        }}
        .brief-content h1 {{
            font-size: 14pt;
            color: #8a7234;
            margin: 28px 0 10px;
            padding-top: 8px;
        }}
        .brief-content h1:first-of-type {{
            margin-top: 0;
        }}
        .brief-content h2 {{
            font-size: 12pt;
            color: #333;
            margin: 20px 0 8px;
        }}
        .brief-content h2.major-section-start {{
            page-break-before: always;
            margin-top: 28px;
        }}
        .brief-content h3 {{
            font-size: 11pt;
            color: #555;
            margin: 14px 0 6px;
        }}
        .brief-content p {{
            margin: 0 0 8px;
        }}
        .brief-content ul, .brief-content ol {{
            margin: 0 0 12px 22px;
        }}
        .brief-content li {{
            margin-bottom: 6px;
        }}
        .brief-content strong.transcript-label,
        .brief-content strong {{
            color: #1a1a1a;
        }}
        .brief-content em {{
            color: #555;
        }}
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
            font-size: 9pt;
            font-weight: bold;
            color: #8a7234;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin: 0 0 8px;
        }}
        .broll-reference-still img {{
            width: 600px;
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            display: block;
            margin: 0 auto;
        }}
        .broll-reference-caption {{
            font-size: 8pt;
            color: #777;
            font-style: italic;
            margin: 8px 0 0;
        }}
        .brief-content hr {{
            border: none;
            border-top: 1px solid #ddd;
            margin: 16px 0;
        }}
        .brief-content pre {{
            font-family: Courier, monospace;
            font-size: 9pt;
            background: #f5f5f0;
            border: 1px solid #ddd;
            padding: 10px;
        }}
        .tldr-box {{
            border: 2px solid #c8a84e;
            background: #fdfbf5;
            padding: 16px 20px;
            margin-bottom: 24px;
            border-radius: 6px;
        }}
        .tldr-box h2 {{
            font-size: 13pt;
            color: #8a7234;
            margin: 0 0 10px;
            border: none;
            padding: 0;
        }}
        .tldr-box p {{
            margin-bottom: 5px;
            font-size: 10.5pt;
        }}
        details.brief-section {{
            margin-bottom: 10px;
        }}
        details.brief-section summary {{
            display: none;
        }}
        .brief-section-body {{
            display: block;
        }}
    </style>
</head>
<body>
    <div class="export-header">
        {logo_img}
        {title_line}
        {subtitle_extra}
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
    print("ISTV B-Roll Letter — Full HTML with Images")
    print("=" * 60)
    print(f"\nClient: {CLIENT_FULL_NAME}")
    print(f"Episode: {EPISODE_TITLE}")
    print()

    new_brief_path = os.path.join(OUTPUT_DIR, "NEW_Rachel_BRoll_Brief.md")
    if not os.path.exists(new_brief_path):
        print(f"ERROR: {new_brief_path} not found. Run generate_comparison.py first.")
        sys.exit(1)

    with open(new_brief_path, "r", encoding="utf-8") as f:
        brief_md = f.read()

    print(f"Loaded brief: {len(brief_md):,} characters")

    gemini_key = get_gemini_api_key()
    client_images = []

    if gemini_key and gemini_key != "your-gemini-key-here" and GEMINI_AVAILABLE:
        print("\nGenerating reference images with Gemini...")
        start = time.time()
        try:
            client_images = generate_location_images(gemini_key, brief_md)
            elapsed = time.time() - start
            print(f"  Generated {len(client_images)} reference images in {elapsed:.1f}s")
            if client_images:
                img_folder = save_images_to_disk(client_images, CLIENT_FULL_NAME)
                print(f"  Images saved to: {img_folder}")
        except Exception as e:
            print(f"  Image generation error (continuing without images): {e}")
    else:
        print("\nGemini not available — generating HTML without reference images.")
        if not GEMINI_AVAILABLE:
            print("  (google-genai package not installed)")
        elif not gemini_key:
            print("  (GEMINI_API_KEY not set in .env)")

    print("\nBuilding enriched HTML with images...")
    enriched_html = build_enriched_brief_html(brief_md, client_images)

    standalone_html = build_standalone_html(
        enriched_html, CLIENT_FULL_NAME, EPISODE_TITLE
    )

    html_path = os.path.join(OUTPUT_DIR, "NEW_Rachel_BRoll_Brief.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(standalone_html)

    print(f"\n{'=' * 60}")
    print(f"DONE! HTML B-Roll letter saved to:")
    print(f"  {html_path}")
    print(f"\n  Images embedded: {len(client_images)}")
    print(f"  File size: {os.path.getsize(html_path) / 1024:.1f} KB")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
