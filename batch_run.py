"""
Batch B-Roll Brief Generator — CLI
===================================
Drop cutsheets into input/ folder, run this script.
HTML files land in output/<timestamp>/ named by client.

Usage:
    python batch_run.py
    python batch_run.py --no-images   (skip Gemini, faster)
"""

import os
import sys
import re
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))

from app import (
    INPUT_DIR,
    ALLOWED_EXTENSIONS,
    AUDIO_EXTENSIONS,
    parse_file,
    build_prompt_text,
    call_claude,
    call_claude_with_text,
    build_client_production_brief_html,
    _extract_episode_title_from_cut_sheet,
    save_to_generated_folder,
    get_logo_base64,
)
from brief_document import export_production_brief_docx

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _build_gdocs_html(brief_html, client_name, episode_title):
    """Build a standalone HTML file ready for copy-paste into Google Docs."""
    logo_b64 = get_logo_base64()
    today = datetime.now().strftime("%B %d, %Y")

    logo_img = ""
    if logo_b64:
        logo_img = f'<img src="data:image/png;base64,{logo_b64}" style="width:200px;margin-bottom:10px;" alt="Inside Success TV">'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{client_name} — Post-Edit B-Roll Brief</title>
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
        .export-header h1 {{
            font-size: 16pt;
            color: #8a7234;
            margin: 0 0 6px;
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
        h2 {{
            font-size: 12pt;
            color: #333;
            margin: 20px 0 8px;
        }}
        h2[style*="page-break-before"] {{
            margin-top: 28px;
        }}
        p {{ margin: 0 0 8px; }}
        ul, ol {{ margin: 0 0 12px 22px; }}
        li {{ margin-bottom: 6px; }}
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
        }}
        details.brief-section {{ margin-bottom: 10px; }}
        details.brief-section summary {{ display: none; }}
        .brief-section-body {{ display: block; }}
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
        hr {{
            border: none;
            border-top: 1px solid #ddd;
            margin: 16px 0;
        }}
    </style>
</head>
<body>
    <div class="export-header">
        {logo_img}
        <h1>POST-EDIT B-ROLL &amp; PRODUCTION BRIEF</h1>
        <p class="subtitle">{client_name} — {episode_title}</p>
        <p class="date">Generated {today}</p>
    </div>
    <div class="brief-content">
        {brief_html}
    </div>
</body>
</html>"""


def _extract_client_name_from_brief(brief_md):
    """Try to pull the client name from the generated brief markdown."""
    match = re.search(r'(?:Dear|Hi|Hey)\s+([A-Z][a-z]+)', brief_md)
    if match:
        return match.group(1)
    return None


def process_single_file(filepath, filename, deadline):
    """Process one cutsheet file → returns (client_name, html_content) or raises."""
    with open(filepath, "rb") as fh:
        file_bytes = fh.read()

    ext = filename.rsplit(".", 1)[1].lower()

    prompt_text = build_prompt_text(
        "[Extract from cut sheet]", "[Extract from cut sheet]",
        "[Extract from cut sheet]", "[Extract from cut sheet]",
        deadline, "None provided.",
    )

    cut_sheet_text = ""
    if ext == "pdf":
        brief_md = call_claude(prompt_text, file_bytes, filename)
    else:
        cut_sheet_text = parse_file(file_bytes, filename)
        brief_md = call_claude_with_text(prompt_text, cut_sheet_text)

    client_name = _extract_client_name_from_brief(brief_md)
    if not client_name:
        client_name = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()

    episode_title = (
        _extract_episode_title_from_cut_sheet(cut_sheet_text)
        if cut_sheet_text
        else "Episode"
    )
    clean_md, html_content = build_client_production_brief_html(
        brief_md, client_name, episode_title, logo_b64=get_logo_base64()
    )

    save_to_generated_folder(client_name, episode_title, clean_md)
    return client_name, html_content, episode_title, clean_md


def main():
    input_files = []
    for f in sorted(os.listdir(INPUT_DIR)):
        ext = f.rsplit(".", 1)[1].lower() if "." in f else ""
        if ext in ALLOWED_EXTENSIONS - AUDIO_EXTENSIONS:
            input_files.append(f)

    if not input_files:
        print("No cutsheet files found in input/ folder.")
        print("Add .xlsx, .pdf, or .txt files and run again.")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"  ISTV Batch B-Roll Brief Generator")
    print(f"  Files: {len(input_files)} | Layout: production v2 (updated-7)")
    print(f"{'='*50}\n")

    for f in input_files:
        print(f"  - {f}")
    print()

    run_folder = os.path.join(OUTPUT_DIR, datetime.now().strftime("%Y-%m-%d_%H%M"))
    os.makedirs(run_folder, exist_ok=True)

    start = time.time()
    results = []

    def _do_one(filename):
        filepath = os.path.join(INPUT_DIR, filename)
        try:
            print(f"  [{filename}] Processing...")
            client_name, html_content, episode_title, clean_md = process_single_file(
                filepath, filename, "TBD"
            )
            safe_name = re.sub(r'[^\w\s-]', '', client_name).strip().replace(' ', '_')
            html_path = os.path.join(run_folder, f"{safe_name}.html")
            md_path = os.path.join(run_folder, f"{safe_name}.md")
            docx_path = os.path.join(run_folder, f"{safe_name}.docx")
            with open(html_path, "w", encoding="utf-8") as fh:
                fh.write(html_content)
            with open(md_path, "w", encoding="utf-8") as fh:
                fh.write(clean_md)
            export_production_brief_docx(html_path, docx_path, md_path)
            print(f"  [{filename}] Done -> {safe_name}.html / .docx")
            return {"file": filename, "ok": True, "client": client_name, "output": html_path}
        except Exception as e:
            print(f"  [{filename}] FAILED: {e}")
            return {"file": filename, "ok": False, "error": str(e)}

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(_do_one, f) for f in input_files]
        for future in as_completed(futures):
            results.append(future.result())

    elapsed = time.time() - start
    succeeded = sum(1 for r in results if r["ok"])

    print(f"\n{'='*50}")
    print(f"  DONE: {succeeded}/{len(results)} briefs in {elapsed:.1f}s")
    print(f"  Output: {run_folder}")
    print(f"{'='*50}\n")

    if succeeded < len(results):
        for r in results:
            if not r["ok"]:
                print(f"  FAILED: {r['file']} — {r['error']}")


if __name__ == "__main__":
    main()
