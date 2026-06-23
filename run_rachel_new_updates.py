"""
Export Rachel B-Roll brief v1 (current 3-column photos table) and v2 (4-column photo format)
into output/Rachels_new_updates/.
"""

import os
import sys
import shutil
import subprocess

sys.path.insert(0, os.path.dirname(__file__))

from brief_document import build_client_brief_html, sanitize_brief_markdown, sanitize_brief_markdown_v2

BASE_DIR = os.path.dirname(__file__)
SOURCE_MD = os.path.join(BASE_DIR, "output", "Rachel_v3_two_page", "Rachel_Fino_BRoll_Brief_v3.md")
OUT_DIR = os.path.join(BASE_DIR, "output", "Rachels_new_updates")

CLIENT_FULL_NAME = "Rachel Fino"
EPISODE_TITLE = "The Woman Who Kept Getting Back Up"


def write_version(label: str, brief_md: str, photos_format: str = "v1") -> None:
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
        [sys.executable, os.path.join(BASE_DIR, "html_to_docx.py"), str(html_path), "-o", str(docx_path)],
        check=False,
    )
    print(f"  {label}: {html_path} ({os.path.getsize(html_path) / 1024:.0f} KB)")


def main():
    if not os.path.isfile(SOURCE_MD):
        print(f"Missing source: {SOURCE_MD}")
        sys.exit(1)

    with open(SOURCE_MD, "r", encoding="utf-8") as f:
        raw_md = f.read()

    os.makedirs(OUT_DIR, exist_ok=True)

    print("Building Rachel brief v1 and v2...")
    v1_md = sanitize_brief_markdown(raw_md)
    v2_md = sanitize_brief_markdown_v2(raw_md)

    write_version("v1", v1_md, photos_format="v1")
    write_version("v2", v2_md, photos_format="v2")

    print(f"\nDone. Both versions saved to:\n  {OUT_DIR}")


if __name__ == "__main__":
    main()
