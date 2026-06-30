# ISTV — Client B-Roll Generation Tool

A production tool for Inside Success TV that generates professional Post-Edit B-Roll & Production Briefs from editor cut sheets. Each request includes verbatim transcript context from the cut sheet so clients understand why each photo or B-roll shot is needed.

Upload a cut sheet (XLSX, PDF, or TXT), and the tool sends everything to Claude AI to produce a complete, branded production brief — available as HTML, DOCX (Word), PDF, or copyable HTML for Google Docs.

## Setup

### 1. Prerequisites

- Python 3.10+
- GTK3 runtime (required by WeasyPrint for PDF generation)
- **Windows DOCX export:** Microsoft Word + `pywin32` (installed via `requirements.txt`)

**Windows — Install GTK3:**

The easiest method is via MSYS2:

1. Download and install MSYS2 from https://www.msys2.org/
2. Open the MSYS2 terminal and run:
   ```
   pacman -S mingw-w64-x86_64-pango mingw-w64-x86_64-gtk3
   ```
3. Add `C:\msys64\mingw64\bin` to your system PATH

Alternatively, download the GTK3 runtime installer from https://github.com/nicedoc/weasyprint/wiki/Installation-on-Windows

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API Keys

Copy the example env file and add your API keys:

```bash
copy .env.example .env
```

Edit `.env` and replace placeholder values with your actual keys (`ANTHROPIC_API_KEY` is required; `GEMINI_API_KEY` is optional for B-roll reference images).

### 4. Logo

The repo includes `static/logo.svg` for branded brief headers. For higher-quality DOCX/PDF output, you can optionally place a `static/logo.png` locally (this file is gitignored so each machine can use its own asset).

### 5. Run the Application

```bash
python app.py
```

Open http://localhost:5000 in your browser.

## Usage

### Single brief (web UI)

1. Fill in the client information (name, episode title, industry)
2. Upload the editor's cut sheet (.xlsx, .pdf, or .txt)
3. Click **Generate Production Brief**
4. Wait for Claude to process (typically 30–60 seconds)
5. Review the output, then:
   - **Copy to Clipboard** — pastes formatted HTML directly into Google Docs
   - **Download PDF** — saves a branded dark-theme PDF
   - **Download DOCX** — Word document with logo, page breaks, and formatted tables

Generated files are also saved under `generated/<Client>_<Episode>_<timestamp>/` as `.md`, `.html`, and `.docx`.

### Bulk generation (CLI)

Drop cut sheets into the `input/` folder, then run:

```bash
python batch_run.py
```

This processes all `.xlsx`, `.xls`, `.pdf`, and `.txt` files in parallel and writes timestamped output to `output/<YYYY-MM-DD_HHMM>/` — each client gets `.md`, `.html`, and `.docx` with the ISTV logo.

### Bulk generation (web UI)

1. Place cut sheets in the `input/` folder
2. Open http://localhost:5000/batch
3. Set an optional deadline and click **Process All**
4. Briefs are saved to `generated/` (and available in the web UI per brief)

### Re-export from existing markdown

To rebuild HTML and DOCX from a saved brief markdown file (no Claude call):

```bash
python export_brief.py tests/fixtures/nilu_naderi_brief_v2.md \
    --client "Nilu Naderi" --episode "The Seed That Waited" -o output/export
```

## File Structure

```
app.py                  Main Flask application
batch_run.py            CLI bulk generator (input/ → output/)
export_brief.py         Re-export markdown → HTML + DOCX
html_to_docx.py         HTML → DOCX via Microsoft Word (Windows)
brief_document.py       Brief layout, HTML builder, DOCX export helper
brief_docx_postprocess.py   Word COM formatting (logo size, page breaks)
requirements.txt        Python dependencies
.env                    API keys (create from .env.example)
input/                  Drop cut sheets here for batch runs (gitignored)
output/                 CLI batch output (gitignored)
generated/              Per-client saved briefs (gitignored)
generated_images/       Gemini reference stills (gitignored)
static/
  style.css             Dark theme stylesheet
  logo.svg              ISTV logo (committed)
templates/
  index.html            Upload form
  batch.html            Bulk processing UI
  result.html           Output viewer with copy/download
  pdf_template.html     PDF rendering template
tests/                  Pytest suite with Nilu Naderi fixture
```

## Notes

- `output/`, `generated/`, `generated_images/`, and `input/` are gitignored — clone the repo and add your own cut sheets locally.
- DOCX export requires Microsoft Word on Windows. On other platforms, HTML and PDF export still work.
- Run tests with `pytest`.
