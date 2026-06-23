"""Export sample briefs to output/updated-12/."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))

from brief_document import build_production_brief

BASE_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.join(BASE_DIR, "output", "updated-12")

EXPORTS = [
    {
        "source": os.path.join(BASE_DIR, "output", "june 3rd", "NILU_NADERI_BRoll_Brief_v2.md"),
        "stem": "Nilu_Naderi_BRoll_Brief_v2",
        "client": "Nilu Naderi",
        "episode": "The Seed That Waited",
    },
    {
        "source": os.path.join(BASE_DIR, "output", "new updates-2", "Rachel_Fino_BRoll_Brief_v1.md"),
        "fallback": os.path.join(BASE_DIR, "output", "Rachels_new_updates", "Rachel_Fino_BRoll_Brief_v1.md"),
        "stem": "Rachel_Fino_BRoll_Brief_v2",
        "client": "Rachel Fino",
        "episode": "The Woman Who Kept Getting Back Up",
    },
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for item in EXPORTS:
        source = item["source"]
        if not os.path.isfile(source) and item.get("fallback"):
            source = item["fallback"]
        if not os.path.isfile(source):
            print(f"Skip missing: {source}")
            continue

        with open(source, encoding="utf-8") as f:
            raw_md = f.read()

        md, html = build_production_brief(raw_md, item["client"], item["episode"])
        md_path = os.path.join(OUT_DIR, f"{item['stem']}.md")
        html_path = os.path.join(OUT_DIR, f"{item['stem']}.html")
        docx_path = os.path.join(OUT_DIR, f"{item['stem']}.docx")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"Exporting {item['client']}...")
        result = subprocess.run(
            [
                sys.executable,
                os.path.join(BASE_DIR, "html_to_docx.py"),
                html_path,
                "-o",
                docx_path,
                "--brief-md",
                md_path,
            ],
            check=False,
        )
        if os.path.isfile(docx_path):
            print(f"  {docx_path} ({os.path.getsize(docx_path) / 1024:.0f} KB)")
        elif result.returncode != 0:
            alt = docx_path.replace(".docx", "_word.docx")
            if os.path.isfile(alt):
                print(f"  saved as {alt}")

    print(f"\nDone. {OUT_DIR}")


if __name__ == "__main__":
    main()
