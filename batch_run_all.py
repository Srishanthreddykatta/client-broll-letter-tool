"""
Batch B-Roll Brief Generator — Full Input Scan
================================================
Recursively scans all input/ subfolders for spreadsheet text files,
deduplicates clients (keeping the latest dated version), and generates
client B-roll letter HTML with reference images.

Usage:
    python batch_run_all.py
    python batch_run_all.py --no-images   (skip Gemini image generation)
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
    build_prompt_text,
    call_claude,
    call_claude_with_text,
    generate_location_images,
    build_client_production_brief_html,
    get_logo_base64,
    save_to_generated_folder,
    get_gemini_api_key,
    get_logo_base64,
    parse_txt,
    GEMINI_AVAILABLE,
    _run_claude_with_retry,
)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _extract_folder_date(folder_name):
    """Extract date from folder name like '2026-05-23_qsaved_1' -> '2026-05-23'."""
    match = re.match(r'(\d{4}-\d{2}-\d{2})', folder_name)
    if match:
        return match.group(1)
    return "0000-00-00"


def _extract_folder_priority(folder_name):
    """Higher priority for 'qsaved' folders (aggregated archives) over 'qroot'."""
    if "qsaved" in folder_name:
        return 2
    if "qroot" in folder_name:
        return 1
    return 0


def _normalize_client_key(filename):
    """Normalize filename to a dedup key (client identity).
    e.g. 'craig_cobb_16-22_mins_spreadsheet_claude_raw.txt' -> 'craig_cobb'
    """
    name = filename.lower().replace(".txt", "")
    name = re.sub(r'_spreadsheet_claude_raw$', '', name)
    name = re.sub(r'_\d+-\d+_mi[ns]+s?$', '', name)
    name = re.sub(r'_\d+-\d+$', '', name)
    name = re.sub(r'_\d+mins?$', '', name)
    # Fix known typos for dedup
    name = name.replace("diana_hamiltion", "diana_hamilton")
    name = name.strip().replace(" ", "_")
    return name


def _client_display_name(filename):
    """Convert filename to a display-friendly client name."""
    name = filename.replace(".txt", "")
    name = re.sub(r'_spreadsheet_claude_raw$', '', name)
    name = re.sub(r'_\d+-\d+_mi[ns]+s?$', '', name)
    name = re.sub(r'_\d+-\d+$', '', name)
    name = re.sub(r'_\d+mins?$', '', name)
    name = name.replace("_", " ").strip().title()
    return name


def discover_spreadsheets():
    """Recursively find all spreadsheet .txt files in input/ subfolders."""
    all_files = []

    for batch_folder in sorted(os.listdir(INPUT_DIR)):
        batch_path = os.path.join(INPUT_DIR, batch_folder)
        if not os.path.isdir(batch_path):
            continue

        spreadsheets_dir = os.path.join(batch_path, "spreadsheets")
        if not os.path.isdir(spreadsheets_dir):
            continue

        folder_date = _extract_folder_date(batch_folder)
        folder_priority = _extract_folder_priority(batch_folder)

        for fname in os.listdir(spreadsheets_dir):
            if not fname.endswith(".txt"):
                continue
            filepath = os.path.join(spreadsheets_dir, fname)
            client_key = _normalize_client_key(fname)
            all_files.append({
                "filepath": filepath,
                "filename": fname,
                "batch_folder": batch_folder,
                "folder_date": folder_date,
                "folder_priority": folder_priority,
                "client_key": client_key,
                "display_name": _client_display_name(fname),
            })

    return all_files


def deduplicate_clients(all_files):
    """Keep only the latest version for each client (by date, then priority)."""
    client_map = {}

    for entry in all_files:
        key = entry["client_key"]
        if key not in client_map:
            client_map[key] = entry
        else:
            existing = client_map[key]
            # Prefer later date, then higher priority folder type
            if (entry["folder_date"], entry["folder_priority"]) > \
               (existing["folder_date"], existing["folder_priority"]):
                client_map[key] = entry

    return sorted(client_map.values(), key=lambda x: x["display_name"])


def _build_gdocs_html(brief_html, client_name, episode_title):
    """Build a standalone HTML file ready for Google Docs."""
    logo_b64 = get_logo_base64()

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
    </div>
    <div class="brief-content">
        {brief_html}
    </div>
</body>
</html>"""


def _extract_client_name_from_brief(brief_md):
    """Pull client name from generated brief greeting."""
    match = re.search(r'(?:Dear|Hi|Hey)\s+([A-Z][a-z]+(?:\s+(?:and\s+)?[A-Z][a-z]+)*)', brief_md)
    if match:
        return match.group(1)
    return None


def _postprocess_brief(brief_md):
    """Remove unwanted elements from Claude's generated output."""
    lines = brief_md.split('\n')
    filtered = []
    for line in lines:
        if re.search(r'\*\*Total items to submit:?\*\*', line, re.IGNORECASE):
            continue
        if re.search(r'support@insidesuccesstv\.com', line, re.IGNORECASE):
            continue
        if re.search(r'\*\*Submit to:?\*\*', line, re.IGNORECASE):
            continue
        filtered.append(line)
    return '\n'.join(filtered)


def _extract_episode_title(cut_sheet_text):
    """Try to extract episode/banner title from spreadsheet JSON content."""
    match = re.search(r'"banner_title":\s*"([^"]+)"', cut_sheet_text)
    if match:
        title = match.group(1)
        # Remove client name prefix if present (format: "Name — Title")
        if " — " in title:
            return title.split(" — ", 1)[1]
        if " - " in title:
            return title.split(" - ", 1)[1]
        return title
    return "Episode"


def process_single_client(entry, gemini_key, gemini_enabled):
    """Process one client's spreadsheet → returns (client_name, html_content, img_count)."""
    filepath = entry["filepath"]
    filename = entry["filename"]
    display_name = entry["display_name"]

    with open(filepath, "rb") as fh:
        file_bytes = fh.read()

    cut_sheet_text = parse_txt(file_bytes)
    episode_title = _extract_episode_title(cut_sheet_text)

    prompt_text = build_prompt_text(
        "[Extract from cut sheet]", "[Extract from cut sheet]",
        "[Extract from cut sheet]", "[Extract from cut sheet]",
        "TBD", "None provided.",
    )

    combined_prompt = (
        f"{prompt_text}\n\n"
        f"---\n\n"
        f"## CUT SHEET CONTENT\n\n"
        f"Below is the full text extracted from the client's cut sheet. "
        f"Use this as your sole source of story information.\n\n"
        f"```\n{cut_sheet_text}\n```"
    )

    content_blocks = [{"type": "text", "text": combined_prompt}]
    brief_md = _run_claude_with_retry(content_blocks)
    brief_md = _postprocess_brief(brief_md)

    client_images = []
    if gemini_enabled:
        try:
            client_images = generate_location_images(gemini_key, brief_md)
        except Exception as e:
            print(f"  [!] Image gen failed for {display_name}: {e}")

    client_name = _extract_client_name_from_brief(brief_md)
    if not client_name:
        client_name = display_name

    clean_md, html_content = build_client_production_brief_html(
        brief_md, client_name, episode_title, logo_b64=get_logo_base64()
    )

    save_to_generated_folder(client_name, episode_title, clean_md)

    return client_name, html_content, len(client_images), episode_title


def _find_existing_outputs():
    """Scan all output/ subfolders for already-generated HTML files."""
    existing = set()
    if not os.path.isdir(OUTPUT_DIR):
        return existing
    for run_folder in os.listdir(OUTPUT_DIR):
        run_path = os.path.join(OUTPUT_DIR, run_folder)
        if not os.path.isdir(run_path):
            continue
        for fname in os.listdir(run_path):
            if fname.endswith(".html"):
                existing.add(fname.lower())
    return existing


def _client_output_filename(entry):
    """Predict what the output filename would be for a client entry."""
    name = entry["display_name"]
    safe = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')
    return f"{safe}.html".lower()


def main():
    skip_images = "--no-images" in sys.argv

    print(f"\n{'='*60}")
    print(f"  ISTV Full Batch B-Roll Brief Generator")
    print(f"  Scanning all input/ subfolders...")
    print(f"{'='*60}\n")

    all_files = discover_spreadsheets()
    print(f"  Found {len(all_files)} total spreadsheet files across all batches.\n")

    unique_clients = deduplicate_clients(all_files)
    duplicates_removed = len(all_files) - len(unique_clients)

    existing_outputs = _find_existing_outputs()
    to_process = []
    skipped = []
    for entry in unique_clients:
        predicted_file = _client_output_filename(entry)
        if predicted_file in existing_outputs:
            skipped.append(entry)
        else:
            to_process.append(entry)

    print(f"  Unique clients after deduplication: {len(unique_clients)}")
    if duplicates_removed:
        print(f"  Duplicates eliminated (older versions): {duplicates_removed}")
    if skipped:
        print(f"  Already generated (skipping): {len(skipped)}")
    print(f"  Clients to generate: {len(to_process)}")
    print(f"  Image generation: {'OFF' if skip_images else 'ON'}")

    if skipped:
        print(f"\n  Skipped (already exist):")
        for entry in skipped:
            print(f"    - {entry['display_name']}")

    if not to_process:
        print(f"\n  All clients already have B-roll letters generated. Nothing to do.")
        return

    print(f"\n  {'—'*50}")
    print(f"  Clients to process:")
    print(f"  {'—'*50}")
    for i, entry in enumerate(to_process, 1):
        print(f"  {i:3d}. {entry['display_name']:<35} (from {entry['batch_folder']})")
    print()

    gemini_key = None if skip_images else get_gemini_api_key()
    gemini_enabled = (
        gemini_key and gemini_key != "your-gemini-key-here"
        and GEMINI_AVAILABLE and not skip_images
    )

    run_folder = os.path.join(OUTPUT_DIR, datetime.now().strftime("%Y-%m-%d_%H%M"))
    os.makedirs(run_folder, exist_ok=True)

    start = time.time()
    results = []
    total = len(to_process)

    def _do_one(entry, index):
        try:
            print(f"  [{index}/{total}] Processing {entry['display_name']}...")
            client_name, html_content, img_count, ep_title = process_single_client(
                entry, gemini_key, gemini_enabled
            )
            safe_name = re.sub(r'[^\w\s-]', '', client_name).strip().replace(' ', '_')
            if not safe_name:
                safe_name = entry['client_key'].replace(' ', '_').title()
            out_path = os.path.join(run_folder, f"{safe_name}.html")
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(html_content)
            print(f"  [{index}/{total}] Done -> {safe_name}.html ({img_count} images)")
            return {
                "file": entry['filename'],
                "ok": True,
                "client": client_name,
                "output": out_path,
                "images": img_count,
            }
        except Exception as e:
            print(f"  [{index}/{total}] FAILED {entry['display_name']}: {e}")
            return {"file": entry['filename'], "ok": False, "error": str(e)}

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_do_one, entry, i): entry
            for i, entry in enumerate(to_process, 1)
        }
        for future in as_completed(futures):
            results.append(future.result())

    elapsed = time.time() - start
    succeeded = sum(1 for r in results if r["ok"])
    total_images = sum(r.get("images", 0) for r in results if r["ok"])

    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE")
    print(f"  {'—'*50}")
    print(f"  Briefs generated: {succeeded}/{total}")
    print(f"  Total images embedded: {total_images}")
    print(f"  Time elapsed: {elapsed:.1f}s")
    print(f"  Output folder: {run_folder}")
    print(f"{'='*60}\n")

    if succeeded < len(results):
        print("  FAILURES:")
        for r in results:
            if not r["ok"]:
                print(f"    - {r['file']}: {r['error']}")
        print()

    # Summary of successful outputs
    if succeeded > 0:
        print("  Generated files:")
        for r in sorted(results, key=lambda x: x.get("client", "")):
            if r["ok"]:
                print(f"    - {r['client']}.html ({r['images']} images)")
        print()


if __name__ == "__main__":
    main()
