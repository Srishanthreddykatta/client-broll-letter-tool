"""
Export a B-Roll brief markdown file to production HTML and DOCX.

Usage:
    python export_brief.py tests/fixtures/nilu_naderi_brief_v2.md \\
        --client "Nilu Naderi" --episode "The Seed That Waited" -o output/export

    python export_brief.py brief.md --client "Client Name" --episode "Episode Title"
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))

from brief_document import build_production_brief


def main() -> int:
    parser = argparse.ArgumentParser(description="Export B-Roll brief to HTML and DOCX")
    parser.add_argument("source_md", help="Path to source brief markdown")
    parser.add_argument("--client", required=True, help="Client full name")
    parser.add_argument("--episode", required=True, help="Episode title")
    parser.add_argument(
        "-o",
        "--out-dir",
        default=os.path.join(os.path.dirname(__file__), "output", "export"),
        help="Output directory (default: output/export)",
    )
    parser.add_argument(
        "--stem",
        help="Output filename stem (default: derived from source filename)",
    )
    args = parser.parse_args()

    source = os.path.abspath(args.source_md)
    if not os.path.isfile(source):
        print(f"ERROR: source not found: {source}")
        return 1

    stem = args.stem or os.path.splitext(os.path.basename(source))[0]
    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    with open(source, encoding="utf-8") as f:
        raw_md = f.read()

    md, html = build_production_brief(raw_md, args.client, args.episode)
    md_path = os.path.join(out_dir, f"{stem}.md")
    html_path = os.path.join(out_dir, f"{stem}.html")
    docx_path = os.path.join(out_dir, f"{stem}.docx")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Wrote {md_path}")
    print(f"Wrote {html_path}")

    result = subprocess.run(
        [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "html_to_docx.py"),
            html_path,
            "-o",
            docx_path,
            "--brief-md",
            md_path,
        ],
        check=False,
    )
    if os.path.isfile(docx_path):
        print(f"Wrote {docx_path} ({os.path.getsize(docx_path) / 1024:.0f} KB)")
    elif result.returncode != 0:
        print("WARNING: DOCX export failed — close any open Word file and retry.")
        return result.returncode

    print(f"\nDone. {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
