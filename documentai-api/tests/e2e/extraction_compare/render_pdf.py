"""Render extraction compare markdown files to a single PDF.

Expects /data to be mounted with the extraction_compare results directory structure:
  /data/extraction_compare_summary.md
  /data/md/*.md
  /data/charts/*.png
  /data/extraction_compare.pdf  (output)
"""

import re
import subprocess
from pathlib import Path

DATA = Path("/data")
CSS = Path("/render_pdf.css")
OUTPUT = DATA / "DocumentAI - Extraction Comparison.pdf"

# Columns to keep (0-indexed) from the Field Comparison table
# Full columns: Field(0), Expected(1), Primary Value(2), OCR/LLM Value(3),
#               Primary Conf(4), OCR/LLM Conf(5), Expected BB(6), Primary BB(7), OCR/LLM BB(8)
_KEEP_COLS = {0, 1, 2, 3}


def _slim_field_comparison_tables(html: str) -> str:
    """Drop conf and bounding box columns from Field Comparison tables."""

    def _process_row(m: re.Match[str]) -> str:
        row_open, content, row_close = m.group(1), m.group(2), m.group(3)
        cells = re.findall(r"<(?:th|td)\b.*?</(?:th|td)>", content, re.DOTALL)
        if len(cells) != 9:
            return str(m.group(0))
        kept = "".join(cells[i] for i in sorted(_KEEP_COLS))
        return f"{row_open}{kept}{row_close}"

    return re.sub(r"(<tr[^>]*>)(.*?)(</tr>)", _process_row, html, flags=re.DOTALL)


def _md_to_html(md_path: Path, base_dir: Path) -> str:
    result = subprocess.run(
        ["pandoc", "--from=markdown", "--to=html", str(md_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    html = result.stdout
    # Rewrite relative image paths to absolute so weasyprint can find them
    html = re.sub(
        r'src="([^"]+)"',
        lambda m: f'src="{(base_dir / m.group(1)).resolve()}"',
        html,
    )
    return html


def main() -> None:
    sections: list[str] = []

    summary = DATA / "extraction_compare_summary.md"
    if summary.exists():
        html = _md_to_html(summary, DATA)
        # Rewrite md links to fragment hrefs and tag each <tr> with the stem id
        html = re.sub(r'href="md/([^"]+)\.md"', lambda m: f'href="#{m.group(1)}"', html)
        html = re.sub(
            r'(<tr[^>]*>)\s*<td>\s*<a\s*\nhref="#([^"]+)"',
            lambda m: f'<tr id="{m.group(2)}-row"><td><a href="#{m.group(2)}"',
            html,
        )
        sections.append(f'<div id="top">{html}</div>')

    for md in sorted((DATA / "md").glob("*.md")):
        sections.append(f'<div class="page-break" id="{md.stem}"></div>')
        html = _slim_field_comparison_tables(_md_to_html(md, DATA / "md"))
        html = re.sub(
            r"<h1([^>]*)>(.*?)</h1>",
            lambda m: f"<h1{m.group(1)}>{m.group(2)}</h1>",
            html,
            count=1,
        )
        html += '<p style="text-align:right;"><a href="#document-summary">↑ Return to Document Summary</a></p>'
        sections.append(html)

    css_text = CSS.read_text() if CSS.exists() else ""
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>{css_text}</style>
</head>
<body>
{"".join(sections)}
</body>
</html>"""

    from weasyprint import HTML  # type: ignore[import-not-found]

    HTML(string=html, base_url=str(DATA)).write_pdf(str(OUTPUT))
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
