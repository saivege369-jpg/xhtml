from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path

from lxml import etree
from xhtml2pdf import pisa

def build_footer_html(patient_name: str, dob: str, date_of_visit: str) -> str:
    parts = []
    if patient_name.strip():
        parts.append(patient_name.strip())
    if dob.strip():
        parts.append(f"DOB: {dob.strip()}")
    if date_of_visit.strip():
        parts.append(f"Date of Visit: {date_of_visit.strip()}")
    footer_text = " ".join(parts)

    # xhtml2pdf header/footer uses special @page frames
    return f"""
    <style>
      @page {{
        size: Letter;
        margin: 0.75in 0.6in 0.75in 0.6in;

        @frame footer_frame {{
          -pdf-frame-content: footer_content;
          left: 0.6in;
          width: 7.3in;
          top: 10.6in;
          height: 0.4in;
        }}
      }}
      #footer_content {{
        font-size: 8pt;
        color: #444444;
        text-align: center;
      }}
    </style>

    <div id="footer_content">{escape_html(footer_text)}</div>
    """

def escape_html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )

def extract_patient_fields(xml_doc: etree._ElementTree) -> tuple[str, str, str]:
    """
    Best-effort extraction. Adjust XPaths if your XML differs.
    If you already compute these in Python elsewhere, pass them via args instead.
    """
    # Try a few common patterns (HL7-ish). This is "best effort".
    def xp(expr: str) -> str:
        try:
            v = xml_doc.xpath(expr)
            if isinstance(v, list):
                v = v[0] if v else ""
            return str(v).strip()
        except Exception:
            return ""

    given1 = xp("string(/ClinicalDocument/patient/given[1])")
    given2 = xp("string(/ClinicalDocument/patient/given[2])")
    family = xp("string(/ClinicalDocument/patient/family)")
    dob = xp("string(/ClinicalDocument/patient/dob)")
    visit = xp("string(/ClinicalDocument/visitDate)")

    name_parts = [p for p in [given1, given2, family] if p]
    full_name = " ".join(name_parts).strip()

    return full_name, dob, visit

def transform_xml_to_xhtml(xml_path: Path, xsl_path: Path) -> bytes:
    xml_doc = etree.parse(str(xml_path))
    xsl_doc = etree.parse(str(xsl_path))
    transform = etree.XSLT(xsl_doc)
    result = transform(xml_doc)

    return etree.tostring(
        result,
        pretty_print=True,
        encoding="UTF-8",
        xml_declaration=True,
    )

def ensure_xhtml_wrapped(xhtml_bytes: bytes, footer_block: str) -> str:
    """
    xhtml2pdf wants a full XHTML/HTML document.
    If the transform already outputs <html>...</html>, we inject footer CSS/content.
    Otherwise we wrap it.
    """
    xhtml = xhtml_bytes.decode("utf-8", errors="replace")

    lower = xhtml.lower()
    if "<html" in lower:
        if "</head>" in lower:
            idx = lower.rfind("</head>")
            xhtml = xhtml[:idx] + footer_block + xhtml[idx:]
        elif "<body" in lower:
            bidx = lower.find("<body")
            open_end = lower.find(">", bidx)
            if open_end != -1:
                xhtml = xhtml[:open_end+1] + footer_block + xhtml[open_end+1:]
        else:
            xhtml = footer_block + xhtml
        return xhtml

    return f"""
    <!doctype html>
<html>
<head>
<meta charset="utf-8"/>
{footer_block}
</head>
<body>
{xhtml}
</body>
</html>
"""

def xhtml_to_pdf(xhtml: str, pdf_path: Path, base_dir: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    def link_callback(uri: str, rel: str | None = None) -> str:
        if uri.startswith(("http://", "https://", "file:/")):
            return uri
        candidate = (base_dir / uri).resolve()
        return str(candidate)

    with open(pdf_path, "wb") as f:
        result = pisa.CreatePDF(
            src=xhtml,
            dest=f,
            encoding="utf-8",
            link_callback=link_callback
        )

    if result.err:
        raise RuntimeError("xhtml2pdf failed to generate PDF (see logs/output).")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", required=True, help="Input XML path")
    ap.add_argument("--xsl", required=True, help="XSL stylesheet path (client/Healow)")
    ap.add_argument("--out", required=True, help="Output PDF path")
    ap.add_argument("--patientName", default="", help="Override patient name for footer")
    ap.add_argument("--dob", default="", help="Override DOB for footer")
    ap.add_argument("--dateOfVisit", default="", help="Override Date of Visit for footer")
    args = ap.parse_args()

    xml_path = Path(args.xml)
    xsl_path = Path(args.xsl)
    pdf_path = Path(args.out)

    if not xml_path.exists():
        raise FileNotFoundError(f"XML not found: {xml_path}")
    if not xsl_path.exists():
        raise FileNotFoundError(f"XSL not found: {xsl_path}")

    xml_doc = etree.parse(str(xml_path))
    auto_name, auto_dob, auto_visit = extract_patient_fields(xml_doc)

    patient_name = args.patientName or auto_name
    dob = args.dob or auto_dob
    date_of_visit = args.dateOfVisit or auto_visit

    xhtml_bytes = transform_xml_to_xhtml(xml_path, xsl_path)

    footer_block = build_footer_html(patient_name, dob, date_of_visit)

    xhtml_full = ensure_xhtml_wrapped(xhtml_bytes, footer_block)

    base_dir = xml_path.parent.resolve()  
    xhtml_to_pdf(xhtml_full, pdf_path, base_dir)

    print(f"[OK] PDF generated: {pdf_path.resolve()}")

if __name__ == "__main__":
    main()
