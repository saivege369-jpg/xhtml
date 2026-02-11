Below are complete Linux steps (no sudo) using Micromamba, plus complete working code (XML+XSL → XHTML → PDF using WeasyPrint 52.5). This avoids the Pango symbol error by bundling Pango/Cairo inside the env.

A) Complete Linux setup (Micromamba, no sudo)
1) Install micromamba into ~/bin
cd ~
curl -L https://micro.mamba.pm/api/micromamba/linux-64/latest -o micromamba.tar.bz2
tar -xjf micromamba.tar.bz2

mkdir -p ~/bin
mv bin/micromamba ~/bin/
export PATH=~/bin:$PATH

2) Enable micromamba activate in your shell (bash)
eval "$(micromamba shell hook -s bash)"


If you want this permanently (so you don’t re-run it every time), add this line to ~/.bashrc:

echo 'export PATH=~/bin:$PATH' >> ~/.bashrc
echo 'eval "$(micromamba shell hook -s bash)"' >> ~/.bashrc
source ~/.bashrc

3) Create a WeasyPrint environment with bundled native libs
micromamba create -y -n wp -c conda-forge \
  python=3.10 \
  weasyprint=52.5 \
  lxml \
  pango cairo harfbuzz gdk-pixbuf libffi fontconfig

4) Activate the environment
micromamba activate wp

5) Verify (this is the key check)
python -m weasyprint --info


You should see output including:

WeasyPrint version: 52.5

Pango version: 1.44+ (often 1.50+)

and it should not be using /lib64/libpango-1.0.so.0

B) Complete code: convert_weasy.py

Save this as convert_weasy.py:

#!/usr/bin/env python3
"""
Convert XML + XSLT -> XHTML (lxml) -> PDF (WeasyPrint 52.5)

Usage:
  python convert_weasy.py input.xml style.xsl output.pdf

Notes:
- Does NOT modify XML or XSL.
- Uses base_url so relative images/CSS referenced by the generated XHTML resolve.
"""

import sys
from pathlib import Path
from lxml import etree
from weasyprint import HTML


def xml_xsl_to_xhtml(xml_path: Path, xsl_path: Path) -> str:
    """Apply XSLT to XML and return XHTML as a string."""
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        recover=False,
        huge_tree=False,
        remove_blank_text=False,
    )

    xml_doc = etree.parse(str(xml_path), parser)
    xsl_doc = etree.parse(str(xsl_path), parser)

    transform = etree.XSLT(xsl_doc)
    result = transform(xml_doc)

    return str(result)


def xhtml_to_pdf(xhtml: str, pdf_path: Path, base_url: str) -> None:
    """Render XHTML string to PDF with WeasyPrint."""
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=xhtml, base_url=base_url).write_pdf(str(pdf_path))


def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: python convert_weasy.py input.xml style.xsl output.pdf")
        return 2

    xml_path = Path(sys.argv[1]).expanduser().resolve()
    xsl_path = Path(sys.argv[2]).expanduser().resolve()
    pdf_path = Path(sys.argv[3]).expanduser().resolve()

    if not xml_path.exists():
        print(f"ERROR: XML not found: {xml_path}", file=sys.stderr)
        return 1
    if not xsl_path.exists():
        print(f"ERROR: XSL not found: {xsl_path}", file=sys.stderr)
        return 1

    # 1) XML + XSL -> XHTML
    xhtml = xml_xsl_to_xhtml(xml_path, xsl_path)

    # Optional: write the generated XHTML for debugging
    # debug_path = xml_path.parent / "debug.xhtml"
    # debug_path.write_text(xhtml, encoding="utf-8")

    # 2) XHTML -> PDF
    # base_url is important for resolving relative URLs in <img src="...">, <link href="...">, etc.
    base_url = str(xml_path.parent)
    xhtml_to_pdf(xhtml, pdf_path, base_url)

    print(f"✅ PDF generated: {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

C) Run the conversion

From the same folder (or give full paths):

micromamba activate wp
python convert_weasy.py input.xml style.xsl output.pdf

D) If assets (images/css) are not found

WeasyPrint resolves relative paths based on:

base_url = str(xml_path.parent)


So ensure any referenced assets are reachable relative to the XML’s directory.

If your assets live elsewhere, change base_url to that folder, e.g.:

base_url = "/path/to/assets"


If your shell is not bash (e.g., csh/tcsh), tell me which one and I’ll give the exact activation commands for that shell too.
