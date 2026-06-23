"""
Convert a B-Roll brief HTML file to .docx (Word).
Uses Microsoft Word on Windows (required for correct tables, page breaks, styling).
Optional --brief-md enables COM post-processing (page breaks, closing box).
"""

import argparse
import sys
import time
from pathlib import Path


def _com_retry(action, retries: int = 6, delay: float = 0.6):
    last_exc = None
    for _ in range(retries):
        try:
            return action()
        except Exception as exc:
            last_exc = exc
            time.sleep(delay)
    raise last_exc


def convert_with_word(html_path: Path, docx_path: Path, brief_md: str | None = None) -> bool:
    try:
        import win32com.client
    except ImportError:
        print("ERROR: pywin32 is required for Word conversion (pip install pywin32).")
        return False

    html_path = html_path.resolve()
    docx_path = docx_path.resolve()

    from brief_docx_postprocess import _word_quiet, apply_brief_formatting_to_doc

    word = None
    doc = None
    try:
        word = win32com.client.gencache.EnsureDispatch("Word.Application")
        _word_quiet(word)
        doc = word.Documents.Open(
            str(html_path),
            ConfirmConversions=False,
            ReadOnly=False,
            AddToRecentFiles=False,
            NoEncodingDialog=True,
        )
        time.sleep(1.5)
        if brief_md:
            try:
                _com_retry(lambda: apply_brief_formatting_to_doc(doc, brief_md))
                print("Applied Word formatting (page breaks, closing).")
            except Exception as exc:
                print(f"Warning: formatting pass skipped ({exc})")
        target = docx_path
        try:
            if target.exists():
                target.unlink()
        except OSError:
            target = docx_path.with_name(f"{docx_path.stem}_word{docx_path.suffix}")
            print(f"Warning: {docx_path.name} is locked — saving as {target.name}")
        _com_retry(lambda: doc.SaveAs2(str(target), FileFormat=16))
        doc.Close(False)
        doc = None
        return target.exists()
    except Exception as exc:
        print(f"Word conversion failed: {exc}")
        return False
    finally:
        if doc is not None:
            try:
                doc.Close(False)
            except Exception:
                pass
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass


def convert_with_html4docx(html_path: Path, docx_path: Path) -> bool:
    try:
        from docx import Document
        from html4docx import HtmlToDocx
    except ImportError:
        return False

    html = html_path.read_text(encoding="utf-8")
    doc = Document()
    HtmlToDocx().add_html_to_document(html, doc)
    doc.save(str(docx_path))
    return docx_path.exists()


def main():
    parser = argparse.ArgumentParser(description="Convert B-Roll brief HTML to DOCX")
    parser.add_argument("html", nargs="?", help="Path to .html file")
    parser.add_argument("-o", "--output", help="Output .docx path (optional)")
    parser.add_argument(
        "--brief-md",
        help="Source markdown for layout plan (enables DOCX post-processing)",
    )
    parser.add_argument(
        "--fallback",
        action="store_true",
        help="Allow html4docx fallback if Word fails (lower fidelity — not recommended)",
    )
    args = parser.parse_args()

    if args.html:
        html_path = Path(args.html)
    else:
        html_path = Path(__file__).parent / "output" / "Rachel_v3_two_page" / "Rachel_Fino_BRoll_Brief_v3.html"

    if not html_path.exists():
        print(f"ERROR: File not found: {html_path}")
        sys.exit(1)

    docx_path = Path(args.output) if args.output else html_path.with_suffix(".docx")

    print(f"Input:  {html_path}")
    print(f"Output: {docx_path}")

    brief_md = None
    if args.brief_md:
        brief_md_path = Path(args.brief_md)
        if brief_md_path.is_file():
            brief_md = brief_md_path.read_text(encoding="utf-8")

    if convert_with_word(html_path, docx_path, brief_md=brief_md):
        print("Converted with Microsoft Word.")
    elif args.fallback and convert_with_html4docx(html_path, docx_path):
        print("WARNING: Converted with html4docx fallback — tables/page breaks may differ from Word export.")
    else:
        print("ERROR: Word conversion failed. Close any open copy of the .docx/.html in Word, then retry.")
        sys.exit(1)

    size_kb = docx_path.stat().st_size / 1024
    print(f"Done. Size: {size_kb:.0f} KB")


if __name__ == "__main__":
    main()
