import os
import sys
import subprocess
from pathlib import Path
import markdown

CSS_STYLE = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap');

@page {
    size: A4;
    margin: 20mm;
}

@media print {
    body {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
        background-color: #ffffff;
    }
}

body {
    font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #1e293b;
    background-color: #ffffff;
    line-height: 1.6;
    font-size: 10.5pt;
    margin: 0;
    padding: 0;
}

h1, h2, h3, h4, h5, h6 {
    color: #0f172a;
    font-weight: 700;
    margin-top: 1.8rem;
    margin-bottom: 0.8rem;
    break-after: avoid;
    -webkit-break-after: avoid;
}

h1 {
    font-size: 24pt;
    border-bottom: 3px solid #6366f1;
    padding-bottom: 8px;
    margin-top: 0;
}

h2 {
    font-size: 16pt;
    border-bottom: 1px solid #cbd5e1;
    padding-bottom: 6px;
}

h3 {
    font-size: 13pt;
}

p {
    margin-top: 0;
    margin-bottom: 1rem;
}

a {
    color: #4f46e5;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

/* Elegant callouts for blockquotes */
blockquote {
    background-color: #f8fafc;
    border-left: 4px solid #6366f1;
    padding: 12px 18px;
    margin: 1.5rem 0;
    border-radius: 0 8px 8px 0;
    color: #475569;
    font-style: italic;
}

blockquote p {
    margin-bottom: 0;
}

/* Beautiful custom tables */
table {
    border-collapse: collapse;
    width: 100%;
    margin-top: 1rem;
    margin-bottom: 2rem;
    font-size: 9.5pt;
    break-inside: avoid;
    -webkit-break-inside: avoid;
}

tr {
    break-inside: avoid;
    -webkit-break-inside: avoid;
}

th {
    background-color: #f1f5f9;
    color: #334155;
    font-weight: 600;
    text-align: left;
    padding: 10px 12px;
    border: 1px solid #cbd5e1;
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

td {
    padding: 10px 12px;
    border: 1px solid #e2e8f0;
    vertical-align: top;
    line-height: 1.5;
}

tr:nth-child(even) {
    background-color: #f8fafc;
}

/* Code styling */
pre {
    background-color: #0f172a;
    color: #f8fafc;
    padding: 14px 18px;
    border-radius: 8px;
    font-family: 'Fira Code', 'Courier New', monospace;
    font-size: 9pt;
    overflow-x: auto;
    line-height: 1.5;
    margin: 1.5rem 0;
    break-inside: avoid;
    -webkit-break-inside: avoid;
}

code {
    font-family: 'Fira Code', 'Courier New', monospace;
    font-size: 9.5pt;
}

p code, li code, td code {
    background-color: #f1f5f9;
    color: #e11d48;
    padding: 2px 6px;
    border-radius: 4px;
}

/* Lists formatting */
ul, ol {
    padding-left: 20px;
    margin-top: 0;
    margin-bottom: 1.2rem;
}

li {
    margin-bottom: 0.5rem;
}

hr {
    border: 0;
    border-top: 1px solid #e2e8f0;
    margin: 2rem 0;
}
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        {css}
    </style>
</head>
<body>
    {content}
</body>
</html>
"""

def get_title_from_md(md_content: str) -> str:
    """Extracts the first H1 header from the markdown to use as the title."""
    for line in md_content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "Document"

def convert_markdown_to_pdf(md_file_path: Path, pdf_file_path: Path):
    print(f"Reading markdown from {md_file_path}...")
    with open(md_file_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Convert MD to HTML using standard markdown module extensions
    print("Converting markdown to HTML...")
    html_content = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])
    title = get_title_from_md(md_text)

    # Wrap in our template with gorgeous styling
    full_html = HTML_TEMPLATE.format(title=title, css=CSS_STYLE, content=html_content)

    temp_html_path = md_file_path.with_suffix(".temp.html")
    print(f"Writing temporary HTML to {temp_html_path}...")
    with open(temp_html_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    try:
        # Construct PDF path and ensure parent dir exists
        pdf_file_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Generating PDF at {pdf_file_path} via Playwright Chromium...")

        # Absolute paths for CLI command (using forward slashes)
        html_abs_str = str(temp_html_path.resolve()).replace("\\", "/")
        pdf_abs_str = str(pdf_file_path.resolve()).replace("\\", "/")

        # Run npx playwright pdf
        cmd = [
            "npx", "playwright", "pdf",
            "--paper-format", "A4",
            html_abs_str,
            pdf_abs_str
        ]
        
        print(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True, encoding='utf-8')
        print(f"Playwright finished successfully. Output:\n{result.stdout}")
        
    except subprocess.CalledProcessError as e:
        print(f"Error executing playwright: {e}")
        print(f"Stderr:\n{e.stderr}")
        raise e
    finally:
        # Cleanup
        if temp_html_path.exists():
            print(f"Cleaning up {temp_html_path}...")
            temp_html_path.unlink()

if __name__ == "__main__":
    project_root = Path(r"c:\Users\91904\Downloads\multimodal-demo")
    backend_dir = project_root / "backend"
    
    files_to_convert = [
        (backend_dir / "cloud_provider_table.md", project_root / "cloud_provider_table.pdf"),
        (backend_dir / "model_speeds_table.md", project_root / "model_speeds_table.pdf")
    ]
    
    success = True
    for md_path, pdf_path in files_to_convert:
        if not md_path.exists():
            print(f"Skipping: {md_path} does not exist.")
            continue
        try:
            convert_markdown_to_pdf(md_path, pdf_path)
            print(f"Successfully generated {pdf_path}\n" + "-"*50)
        except Exception as ex:
            print(f"Failed to convert {md_path}: {ex}")
            success = False
            
    if not success:
        sys.exit(1)
    print("All conversions complete!")
