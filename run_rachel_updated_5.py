"""

Export Rachel B-Roll brief v2 to output/updated-5/ with Word COM post-processing.

"""



import os

import sys

import subprocess



sys.path.insert(0, os.path.dirname(__file__))



from brief_document import build_client_brief_html, sanitize_brief_markdown_v2



BASE_DIR = os.path.dirname(__file__)

SOURCE_MD = os.path.join(

    BASE_DIR, "output", "new updates-2", "Rachel_Fino_BRoll_Brief_v1.md"

)

FALLBACK_MD = os.path.join(

    BASE_DIR, "output", "Rachels_new_updates", "Rachel_Fino_BRoll_Brief_v1.md"

)

OUT_DIR = os.path.join(BASE_DIR, "output", "updated-5")



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

    v2_md = sanitize_brief_markdown_v2(raw_md)



    html = build_client_brief_html(

        v2_md, CLIENT_FULL_NAME, EPISODE_TITLE, photos_format="v2", skip_sanitize=True

    )



    md_path = os.path.join(OUT_DIR, "Rachel_Fino_BRoll_Brief_v2.md")

    html_path = os.path.join(OUT_DIR, "Rachel_Fino_BRoll_Brief_v2.html")

    docx_path = os.path.join(OUT_DIR, "Rachel_Fino_BRoll_Brief_v2.docx")



    with open(md_path, "w", encoding="utf-8") as f:

        f.write(v2_md)

    with open(html_path, "w", encoding="utf-8") as f:

        f.write(html)



    print("Building updated-5 export (HTML + Word post-process)...")

    subprocess.run(

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

    print(f"  Rachel_Fino_BRoll_Brief_v2.html ({os.path.getsize(html_path) / 1024:.0f} KB)")

    if os.path.isfile(docx_path):

        print(f"  Rachel_Fino_BRoll_Brief_v2.docx ({os.path.getsize(docx_path) / 1024:.0f} KB)")





if __name__ == "__main__":

    main()


