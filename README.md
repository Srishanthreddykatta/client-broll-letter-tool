# ISTV — Client B-Roll Generation Tool

A production tool for Inside Success TV that generates professional Post-Edit B-Roll & Production Briefs from editor cut sheets. Each request includes verbatim transcript context from the cut sheet so clients understand why each photo or B-roll shot is needed. Export as PDF (client name first in filename), HTML for Google Docs, or copy directly to clipboard.

Upload a cut sheet (XLSX, PDF, or TXT), fill in the client details, and the tool sends everything to Claude AI to produce a complete, branded production brief — available as a downloadable PDF and copyable HTML for Google Docs.

## Setup

### 1. Prerequisites

- Python 3.10+
- GTK3 runtime (required by WeasyPrint for PDF generation)

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

### 3. Configure API Key

Copy the example env file and add your Anthropic API key:

```bash
copy .env.example .env
```

Edit `.env` and replace `your-key-here` with your actual Anthropic API key.

### 4. Run the Application

```bash
python app.py
```

Open http://localhost:5000 in your browser.

## Usage

1. Fill in the client information (name, episode title, industry)
2. Upload the editor's cut sheet (.xlsx, .pdf, or .txt)
3. Click **Generate Production Brief**
4. Wait for Claude to process (typically 30–60 seconds)
5. Review the output, then:
   - **Copy to Clipboard** — pastes formatted HTML directly into Google Docs
   - **Download PDF** — saves a branded dark-theme PDF

## File Structure

```
app.py              Main Flask application
requirements.txt    Python dependencies
.env                API key (create from .env.example)
static/
  style.css         Dark theme stylesheet
  logo.png          ISTV logo
templates/
  index.html        Upload form
  result.html       Output viewer with copy/download
  pdf_template.html PDF rendering template
```
