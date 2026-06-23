"""
Rebuild HTML B-Roll letters from saved markdown briefs in generated/ folder.
Uses existing markdown (no Claude calls needed), regenerates images via Gemini.
"""

import os
import sys
import re
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))

from app import (
    generate_location_images,
    build_enriched_brief_html,
    get_gemini_api_key,
    get_logo_base64,
    GEMINI_AVAILABLE,
)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
GENERATED_DIR = os.path.join(os.path.dirname(__file__), "generated")


def _build_gdocs_html(brief_html, client_name, episode_title):
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


def _postprocess_brief(brief_md):
    """Remove unwanted elements."""
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


def find_latest_briefs():
    """Find the latest markdown brief for each unique client."""
    client_briefs = {}
    
    for folder_name in os.listdir(GENERATED_DIR):
        folder_path = os.path.join(GENERATED_DIR, folder_name)
        if not os.path.isdir(folder_path):
            continue
        
        md_files = [f for f in os.listdir(folder_path) if f.endswith('_BRoll_Brief.md')]
        if not md_files:
            continue
        
        md_path = os.path.join(folder_path, md_files[0])
        client_name = md_files[0].replace('_BRoll_Brief.md', '').replace('_', ' ')
        
        # Extract episode title from folder name
        parts = folder_name.rsplit('_2026-', 1)
        if len(parts) == 2:
            ep_parts = parts[0].split('_', 1)
            if len(ep_parts) == 2:
                episode_title = ep_parts[1].replace('_', ' ')
            else:
                episode_title = "Episode"
        else:
            episode_title = "Episode"
        
        # Extract timestamp for dedup (keep latest)
        date_match = re.search(r'2026-05-30_(\d{4})', folder_name)
        timestamp = date_match.group(1) if date_match else "0000"
        
        key = client_name.lower().strip()
        if key not in client_briefs or timestamp > client_briefs[key]['timestamp']:
            client_briefs[key] = {
                'md_path': md_path,
                'client_name': client_name,
                'episode_title': episode_title,
                'timestamp': timestamp,
                'folder': folder_name,
            }
    
    return sorted(client_briefs.values(), key=lambda x: x['client_name'])


def main():
    skip_images = "--no-images" in sys.argv
    
    print(f"\n{'='*60}")
    print(f"  Rebuilding HTML from existing markdown briefs")
    print(f"{'='*60}\n")
    
    briefs = find_latest_briefs()
    print(f"  Found {len(briefs)} unique client briefs to rebuild.\n")
    
    for i, b in enumerate(briefs, 1):
        print(f"  {i:3d}. {b['client_name']:<30} ({b['timestamp']})")
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
    total = len(briefs)
    
    def _do_one(brief_info, index):
        try:
            with open(brief_info['md_path'], 'r', encoding='utf-8') as f:
                brief_md = f.read()
            
            brief_md = _postprocess_brief(brief_md)
            
            client_images = []
            if gemini_enabled:
                try:
                    client_images = generate_location_images(gemini_key, brief_md)
                except Exception as e:
                    print(f"  [!] Image gen failed for {brief_info['client_name']}: {e}")
            
            brief_html = build_enriched_brief_html(brief_md, client_images)
            html_content = _build_gdocs_html(
                brief_html, 
                brief_info['client_name'], 
                brief_info['episode_title']
            )
            
            safe_name = re.sub(r'[^\w\s-]', '', brief_info['client_name']).strip().replace(' ', '_')
            out_path = os.path.join(run_folder, f"{safe_name}.html")
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(html_content)
            
            print(f"  [{index}/{total}] Done -> {safe_name}.html ({len(client_images)} images)")
            return {"ok": True, "client": brief_info['client_name'], "images": len(client_images)}
        except Exception as e:
            print(f"  [{index}/{total}] FAILED {brief_info['client_name']}: {e}")
            return {"ok": False, "client": brief_info['client_name'], "error": str(e)}
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_do_one, b, i): b
            for i, b in enumerate(briefs, 1)
        }
        for future in as_completed(futures):
            results.append(future.result())
    
    elapsed = time.time() - start
    succeeded = sum(1 for r in results if r["ok"])
    total_images = sum(r.get("images", 0) for r in results if r["ok"])
    
    print(f"\n{'='*60}")
    print(f"  DONE: {succeeded}/{total} rebuilt in {elapsed:.1f}s")
    print(f"  Images: {total_images}")
    print(f"  Output: {run_folder}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
