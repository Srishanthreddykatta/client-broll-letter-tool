"""
Export Rachel B-Roll brief v2 to output/updated-9/.
"""

import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(__file__))

from brief_document import build_production_brief

BASE_DIR = os.path.dirname(__file__)
SOURCE_MD = os.path.join(
    BASE_DIR, "output", "new updates-2", "Rachel_Fino_BRoll_Brief_v1.md"
)
FALLBACK_MD = os.path.join(
    BASE_DIR, "output", "Rachels_new_updates", "Rachel_Fino_BRoll_Brief_v1.md"
)
OUT_DIR = os.path.join(BASE_DIR, "output", "updated-9")

CLIENT_FULL_NAME = "Rachel Fino"
EPISODE_TITLE = "The Woman Who Kept Getting Back Up"


def main():
    source = SOURCE_MD if os.path.isfile(SOURCE_MD) else FALLBACK_MD
    if not os.path.isfile(source):
        print(f"Missing source: {source}")
        sys.exit(1)

    with open(source, "r", encoding="utf-8") as f:
        raw_md = f.read()

    os.makedirs(OUT_DIR, exist_ok=True)

    # Embed logo as base64 in HTML (Word COM opens reliably — same as updated-7).
    v2_md, html = build_production_brief(
        raw_md, CLIENT_FULL_NAME, EPISODE_TITLE
    )

    md_path = os.path.join(OUT_DIR, "Rachel_Fino_BRoll_Brief_v2.md")
    html_path = os.path.join(OUT_DIR, "Rachel_Fino_BRoll_Brief_v2.html")
    docx_path = os.path.join(OUT_DIR, "Rachel_Fino_BRoll_Brief_v2.docx")

    for label, path, content in (
        ("md", md_path, v2_md),
        ("html", html_path, html),
    ):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except PermissionError:
            alt = path.replace("_v2.", "_v2_export.")
            with open(alt, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Warning: {path} is locked — wrote {alt} instead")
            if label == "html":
                html_path = alt

    print("Building updated-9 export...")
    result = subprocess.run(
        [
            sys.executable,
            os.path.join(BASE_DIR, "html_to_docx.py"),
            str(html_path),
            "-o",
            str(docx_path),
            "--brief-md",
            str(md_path),
        ],
        check=False,
    )

    print(f"\nDone.\n  {OUT_DIR}")
    print(f"  {os.path.basename(html_path)} ({os.path.getsize(html_path) / 1024:.0f} KB)")
    if os.path.isfile(docx_path):
        print(f"  Rachel_Fino_BRoll_Brief_v2.docx ({os.path.getsize(docx_path) / 1024:.0f} KB)")
    elif result.returncode != 0:
        alt = docx_path.with_name(f"{docx_path.stem}_word{docx_path.suffix}")
        if alt.is_file():
            print(f"  Word export saved as {alt.name}")


if __name__ == "__main__":
    main()
