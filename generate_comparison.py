"""
Generate a B-Roll Letter for Rachel using the updated prompt_v2.txt,
then save both old and new versions in a comparison folder.
"""

import os
import sys
import shutil
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.insert(0, os.path.dirname(__file__))

import anthropic

CLAUDE_MODEL = "claude-opus-4-20250514"
CLAUDE_MAX_TOKENS = 16384
CLAUDE_TIMEOUT_SECONDS = 600.0

CLIENT_FIRST_NAME = "Rachel"
CLIENT_FULL_NAME = "Rachel Fino"
EPISODE_TITLE = "The Woman Who Kept Getting Back Up"
INDUSTRY = "Women's Health / Medical Aesthetics"
DEADLINE = "TBD"
EDITOR_NOTES = "None provided."

BASE_DIR = os.path.dirname(__file__)
PROMPT_V2_PATH = os.path.join(BASE_DIR, "prompt_v2.txt")
CUT_SHEET_PATH = os.path.join(BASE_DIR, "input", "2026-05-23_qroot_1", "spreadsheets", "rachel_fidino_16-20_mins_spreadsheet_claude_raw.txt")
OLD_BRIEF_PATH = os.path.join(BASE_DIR, "generated", "Rachel_The_Woman_Who_Kept_Getting_Back_Up_2026-05-30_0352", "Rachel_BRoll_Brief.md")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "Rachel_old_vs_new")


def load_prompt_v2():
    with open(PROMPT_V2_PATH, "r", encoding="utf-8") as f:
        prompt = f.read()
    print(f"  Raw prompt_v2.txt length: {len(prompt):,} characters")
    try:
        formatted = prompt.format(
            client_first_name=CLIENT_FIRST_NAME,
            client_full_name=CLIENT_FULL_NAME,
            episode_title=EPISODE_TITLE,
            industry=INDUSTRY,
            deadline=DEADLINE,
            editor_notes=EDITOR_NOTES,
        )
        print(f"  Formatted prompt length: {len(formatted):,} characters")
        return formatted
    except (KeyError, IndexError) as e:
        print(f"  WARNING: .format() failed with {e}, using replace() fallback")
        prompt = prompt.replace("{client_first_name}", CLIENT_FIRST_NAME)
        prompt = prompt.replace("{client_full_name}", CLIENT_FULL_NAME)
        prompt = prompt.replace("{episode_title}", EPISODE_TITLE)
        prompt = prompt.replace("{industry}", INDUSTRY)
        prompt = prompt.replace("{deadline}", DEADLINE)
        prompt = prompt.replace("{editor_notes}", EDITOR_NOTES)
        print(f"  Fallback prompt length: {len(prompt):,} characters")
        return prompt


def load_cut_sheet():
    with open(CUT_SHEET_PATH, "r", encoding="utf-8") as f:
        return f.read()


def generate_brief(prompt_text, cut_sheet_text):
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in .env")

    client = anthropic.Anthropic(api_key=api_key, timeout=CLAUDE_TIMEOUT_SECONDS, max_retries=0)

    full_message = (
        f"{prompt_text}\n\n"
        f"---\n\n"
        f"## CUT SHEET CONTENT\n\n"
        f"Below is the full text extracted from the client's cut sheet. "
        f"Use this as your sole source of story information.\n\n"
        f"```\n{cut_sheet_text}\n```"
    )

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sending request to Claude ({CLAUDE_MODEL})...")
    print(f"  Total message length: {len(full_message):,} characters")

    start = time.time()
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=CLAUDE_MAX_TOKENS,
        temperature=0.4,
        messages=[{"role": "user", "content": [{"type": "text", "text": full_message}]}],
    )
    elapsed = time.time() - start

    result = ""
    for block in message.content:
        if getattr(block, "type", None) == "text":
            result += block.text

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Response received in {elapsed:.1f}s")
    print(f"  Output length: {len(result):,} characters")
    return result


def main():
    print("=" * 60)
    print("ISTV B-Roll Letter - Old vs New Comparison Generator")
    print("=" * 60)
    print(f"\nClient: {CLIENT_FULL_NAME}")
    print(f"Episode: {EPISODE_TITLE}")
    print(f"Using prompt: prompt_v2.txt")
    print()

    print("Loading prompt_v2.txt...")
    prompt_text = load_prompt_v2()

    print("Loading cut sheet...")
    cut_sheet_text = load_cut_sheet()

    print("\nGenerating new brief with updated prompt...")
    new_brief = generate_brief(prompt_text, cut_sheet_text)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    old_dest = os.path.join(OUTPUT_DIR, "OLD_Rachel_BRoll_Brief.md")
    new_dest = os.path.join(OUTPUT_DIR, "NEW_Rachel_BRoll_Brief.md")

    print(f"\nCopying old brief to comparison folder...")
    shutil.copy2(OLD_BRIEF_PATH, old_dest)

    print(f"Saving new brief to comparison folder...")
    with open(new_dest, "w", encoding="utf-8") as f:
        f.write(new_brief)

    readme_content = f"""# Rachel Fino - B-Roll Brief Comparison
## Old vs New (Prompt v2)

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Client:** {CLIENT_FULL_NAME}
**Episode:** {EPISODE_TITLE}

## Files

- `OLD_Rachel_BRoll_Brief.md` - Generated with the original MASTER_PROMPT (from app.py)
- `NEW_Rachel_BRoll_Brief.md` - Generated with the updated prompt_v2.txt

## Key Differences to Look For

1. **AT A GLANCE section** - formatting and structure
2. **Opening Letter** - tone and brevity
3. **Photos & Archival** - one ask per bullet, episode quotes
4. **Video B-Roll shots** - shot labels, context format, location consolidation
5. **General Lifestyle Pool** - numbered format with Shot Label headers
6. **Interview section** - global numbering continuation
7. **Overall formatting** - machine-parsable shot headers, global numbering
"""

    readme_path = os.path.join(OUTPUT_DIR, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"\n{'=' * 60}")
    print(f"DONE! Comparison saved to:")
    print(f"  {OUTPUT_DIR}")
    print(f"\nFiles:")
    print(f"  - OLD_Rachel_BRoll_Brief.md")
    print(f"  - NEW_Rachel_BRoll_Brief.md")
    print(f"  - README.md")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
