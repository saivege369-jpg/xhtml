#!/usr/bin/env python3
"""
XML + XSLT -> XHTML (lxml) -> PDF (xhtml2pdf) with CSS sanitization

Install:
  pip install lxml xhtml2pdf
"""

import re
import sys
from pathlib import Path
from lxml import etree, html
from xhtml2pdf import pisa


# ----------------------------
# 1) XML + XSLT -> XHTML
# ----------------------------
def xml_xsl_to_xhtml(xml_path: Path, xsl_path: Path) -> str:
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


# ----------------------------
# 2) XHTML sanitization for xhtml2pdf
# ----------------------------
def _sanitize_css_text(css: str) -> str:
    """
    Remove CSS constructs that frequently crash xhtml2pdf's CSS parser.
    This targets the exact @page parsing path that throws NotImplementedType.
    """

    # Remove @page and @page:* blocks (most common crash)
    css = re.sub(r"@page\s*[^{}]*\{(?:[^{}]|\{[^{}]*\})*\}", "", css, flags=re.I | re.S)

    # Remove @font-face blocks (sometimes breaks depending on syntax)
    css = re.sub(r"@font-face\s*\{(?:[^{}]|\{[^{}]*\})*\}", "", css, flags=re.I | re.S)

    # Remove other at-rules that xhtml2pdf often can't parse
    css = re.sub(r"@supports\s*[^{}]*\{(?:[^{}]|\{[^{}]*\})*\}", "", css, flags=re.I | re.S)
    css = re.sub(r"@media\s*[^{}]*\{(?:[^{}]|\{[^{}]*\})*\}", "", css, flags=re.I | re.S)
    css = re.sub(r"@keyframes\s*[^{}]*\{(?:[^{}]|\{[^{}]*\})*\}", "", css, flags=re.I | re.S)

    # Remove properties that are frequently problematic (keep it conservative)
    css = re.sub(r"(?i)\bdisplay\s*:\s*flex\s*;?", "", css)
    css = re.sub(r"(?i)\bposition\s*:\s*fixed\s*;?", "", css)

    return css


def sanitize_xhtml_for_xhtml2pdf(xhtml: str, drop_all_css: bool = False) -> str:
    """
    - If drop_all_css=True: remove <style> and <link rel="stylesheet"> entirely.
    - Otherwise: sanitize CSS inside <style> blocks to avoid parser crashes.
    """
    # Parse as HTML fragment/doc robustly
    doc = html.fromstring(xhtml)

    # Remove external stylesheets optionally (xhtml2pdf may fetch them poorly anyway)
    for link in doc.xpath("//link[translate(@rel,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='stylesheet']"):
        link.getparent().remove(link)

    style_nodes = doc.xpath("//style")

    if drop_all_css:
        for st in style_nodes:
            st.getparent().remove(st)
        return html.tostring(doc, encoding="unicode", method="html")

    # Sanitize embedded CSS
    for st in style_nodes:
        css_text = st.text or ""
        st.text = _sanitize_css_text(css_text)

    return html.tostring(doc, encoding="unicode", method="html")


# ----------------------------
# 3) XHTML -> PDF (xhtml2pdf)
# ----------------------------
def xhtml_to_pdf(xhtml: str, pdf_path: Path, base_dir: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    def link_callback(uri: str, rel: str) -> str:
        # Convert file:// URIs to paths
        if uri.startswith("file://"):
            uri = uri.replace("file://", "")

        # Try resolving relative paths against base_dir
        candidate = (base_dir / uri).resolve()
        if candidate.exists():
            return str(candidate)

        return uri  # fallback

    with open(pdf_path, "wb") as f:
        result = pisa.CreatePDF(
            src=xhtml,
            dest=f,
            encoding="utf-8",
            link_callback=link_callback,
        )

    if result.err:
        raise RuntimeError("xhtml2pdf reported errors while generating PDF.")


# ----------------------------
# Main with fallback strategy
# ----------------------------
def main():
    if len(sys.argv) != 4:
        print("Usage: python3 final_test.py input.xml style.xsl output.pdf")
        sys.exit(1)

    xml_path = Path(sys.argv[1]).expanduser().resolve()
    xsl_path = Path(sys.argv[2]).expanduser().resolve()
    pdf_path = Path(sys.argv[3]).expanduser().resolve()

    if not xml_path.exists():
        raise FileNotFoundError(f"XML not found: {xml_path}")
    if not xsl_path.exists():
        raise FileNotFoundError(f"XSL not found: {xsl_path}")

    base_dir = xml_path.parent

    # 1) Transform
    raw_xhtml = xml_xsl_to_xhtml(xml_path, xsl_path)

    # Optional debug: save raw XHTML exactly as produced by XSLT
    # (base_dir / "debug_raw.xhtml").write_text(raw_xhtml, encoding="utf-8")

    # 2) First attempt: sanitize common crashing CSS (@page etc.)
    try:
        cleaned = sanitize_xhtml_for_xhtml2pdf(raw_xhtml, drop_all_css=False)
        # (base_dir / "debug_cleaned.xhtml").write_text(cleaned, encoding="utf-8")
        xhtml_to_pdf(cleaned, pdf_path, base_dir)
        print(f"✅ PDF generated (sanitized CSS): {pdf_path}")
        return
    except Exception as e:
        sys.stderr.write(f"[WARN] First attempt failed: {e}\n")

    # 3) Fallback: drop ALL CSS (brutal but usually produces a PDF)
    try:
        cleaned2 = sanitize_xhtml_for_xhtml2pdf(raw_xhtml, drop_all_css=True)
        # (base_dir / "debug_nocss.xhtml").write_text(cleaned2, encoding="utf-8")
        xhtml_to_pdf(cleaned2, pdf_path, base_dir)
        print(f"✅ PDF generated (NO CSS fallback): {pdf_path}")
        return
    except Exception as e:
        sys.stderr.write(f"[ERROR] Fallback failed too: {e}\n")
        sys.stderr.write(
            "xhtml2pdf likely cannot handle this XHTML/CSS. "
            "At this point, WeasyPrint/Chromium is the practical option.\n"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
