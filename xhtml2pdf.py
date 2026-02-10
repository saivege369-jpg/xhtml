#!/usr/bin/env python3
"""
Convert XML + XSLT -> XHTML -> PDF using lxml + xhtml2pdf

Install:
  pip install lxml xhtml2pdf
"""

import sys
from pathlib import Path
from lxml import etree
from xhtml2pdf import pisa


def xml_xsl_to_xhtml(xml_path: Path, xsl_path: Path) -> str:
    """
    Apply XSLT to XML and return XHTML string.
    """
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


def xhtml_to_pdf(xhtml: str, pdf_path: Path, base_dir: Path):
    """
    Convert XHTML string to PDF.
    """
    def link_callback(uri, rel):
        # Resolve relative paths for images, css, etc.
        path = (base_dir / uri).resolve()
        return str(path) if path.exists() else uri

    with open(pdf_path, "wb") as f:
        pisa.CreatePDF(
            src=xhtml,
            dest=f,
            encoding="utf-8",
            link_callback=link_callback,
        )


def main():
    if len(sys.argv) != 4:
        print("Usage: python convert.py input.xml style.xsl output.pdf")
        sys.exit(1)

    xml_path = Path(sys.argv[1]).resolve()
    xsl_path = Path(sys.argv[2]).resolve()
    pdf_path = Path(sys.argv[3]).resolve()

    if not xml_path.exists():
        raise FileNotFoundError(xml_path)
    if not xsl_path.exists():
        raise FileNotFoundError(xsl_path)

    # Step 1: XML + XSL → XHTML
    xhtml = xml_xsl_to_xhtml(xml_path, xsl_path)

    # (Optional but VERY useful for debugging)
    # Path("debug.xhtml").write_text(xhtml, encoding="utf-8")

    # Step 2: XHTML → PDF
    xhtml_to_pdf(xhtml, pdf_path, base_dir=xml_path.parent)

    print(f"✅ PDF generated: {pdf_path}")


if __name__ == "__main__":
    main()
