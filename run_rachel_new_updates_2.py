"""
Export updated Rachel B-Roll brief v2 (revised photo table columns) to output/new updates-2/.
Uses v1 source markdown for photo data.
"""

import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(__file__))

from brief_document import (
    build_client_brief_html,
    sanitize_brief_markdown,
    sanitize_brief_markdown_v2,
)

BASE_DIR = os.path.dirname(__file__)
SOURCE_V1_MD = os.path.join(
    BASE_DIR, "output", "Rachels_new_updates", "Rachel_Fino_BRoll_Brief_v1.md"
)
FALLBACK_MD = os.path.join(
    BASE_DIR, "output", "Rachel_v3_two_page", "Rachel_Fino_BRoll_Brief_v3.md"
)
OUT_DIR = os.path.join(BASE_DIR, "output", "new updates-2")

CLIENT_FULL_NAME = "Rachel Fino"
EPISODE_TITLE = "The Woman Who Kept Getting Back Up"


def write_version(label: str, brief_md: str, photos_format: str) -> None:
    html = build_client_brief_html(
        brief_md,
        CLIENT_FULL_NAME,
        EPISODE_TITLE,
        photos_format=photos_format,
        skip_sanitize=True,
    )
    md_path = os.path.join(OUT_DIR, f"Rachel_Fino_BRoll_Brief_{label}.md")
    html_path = os.path.join(OUT_DIR, f"Rachel_Fino_BRoll_Brief_{label}.html")
    docx_path = os.path.join(OUT_DIR, f"Rachel_Fino_BRoll_Brief_{label}.docx")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(brief_md)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    subprocess.run(
        [
            sys.executable,
            os.path.join(BASE_DIR, "html_to_docx.py"),
            str(html_path),
            "-o",
            str(docx_path),
        ],
        check=False,
    )
    print(f"  {label}: {html_path} ({os.path.getsize(html_path) / 1024:.0f} KB)")


def main():
    source = SOURCE_V1_MD if os.path.isfile(SOURCE_V1_MD) else FALLBACK_MD
    if not os.path.isfile(source):
        print(f"Missing source markdown: {source}")
        sys.exit(1)

    with open(source, "r", encoding="utf-8") as f:
        raw_md = f.read()

    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"Source: {source}")
    print("Building v1 (reference) + updated v2...")
    v1_md = sanitize_brief_markdown(raw_md)
    v2_md = sanitize_brief_markdown_v2(raw_md)

    write_version("v1", v1_md, "v1")
    write_version("v2", v2_md, "v2")

    print(f"\nDone. Files saved to:\n  {OUT_DIR}")


if __name__ == "__main__":
    main()
