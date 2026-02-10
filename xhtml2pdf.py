#!/usr/bin/env python3
"""
Convert XML + XSLT -> XHTML (via lxml) -> PDF (via xhtml2pdf)

Install:
  pip install lxml xhtml2pdf
"""

import argparse
import os
import sys
from pathlib import Path

from lxml import etree
from xhtml2pdf import pisa


def xslt_xml_to_xhtml(xml_path: Path, xslt_path: Path, xslt_params: dict | None = None) -> str:
    """
    Transform XML using XSLT into an XHTML string.
    """
    # Safer parser defaults (avoid network access / huge trees)
    xml_parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        recover=False,
        huge_tree=False,
        remove_blank_text=False,
    )

    xml_doc = etree.parse(str(xml_path), parser=xml_parser)
    xslt_doc = etree.parse(str(xslt_path), parser=xml_parser)

    transform = etree.XSLT(xslt_doc)

    # XSLT params must be XSLT string objects
    params = {}
    if xslt_params:
        for k, v in xslt_params.items():
            params[k] = etree.XSLT.strparam(str(v))

    result_tree = transform(xml_doc, **params)

    # Convert result to a Unicode string
    xhtml = str(result_tree)

    # Ensure it looks like XHTML (basic sanity check)
    if "<html" not in xhtml.lower():
        # Not fatal, but often indicates the stylesheet isn't producing XHTML
        sys.stderr.write("Warning: XSLT output does not appear to contain an <html> tag.\n")

    return xhtml


def xhtml_to_pdf(xhtml: str, pdf_path: Path, base_dir: Path | None = None) -> None:
    """
    Convert XHTML string to PDF using xhtml2pdf.
    base_dir helps resolve relative URLs in <img src="...">, CSS, etc.
    """
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    # xhtml2pdf can resolve relative resources if you pass a link_callback
    def link_callback(uri: str, rel: str) -> str:
        # If URI is absolute path or URL, return as-is (xhtml2pdf supports some forms)
        # For relative paths, resolve against base_dir.
        if base_dir is None:
            return uri

        # Handle file:// URIs
        if uri.startswith("file://"):
            return uri.replace("file://", "")

        # Resolve relative filesystem paths
        candidate = (base_dir / uri).resolve()
        if candidate.exists():
            return str(candidate)

        # Fall back to original
        return uri

    with open(pdf_path, "wb") as f:
        result = pisa.CreatePDF(
            src=xhtml,
            dest=f,
            encoding="utf-8",
            link_callback=link_callback,
        )

    if result.err:
        raise RuntimeError("xhtml2pdf failed to generate PDF (see stderr/logs).")


def parse_kv_params(param_list: list[str]) -> dict:
    """
    Parse ["k=v", "a=b"] into dict. Used for passing XSLT params.
    """
    params = {}
    for item in param_list:
        if "=" not in item:
            raise ValueError(f"Invalid param '{item}'. Expected format key=value.")
        k, v = item.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            raise ValueError(f"Invalid param '{item}'. Key is empty.")
        params[k] = v
    return params


def main():
    ap = argparse.ArgumentParser(description="XML + XSLT -> XHTML -> PDF")
    ap.add_argument("--xml", required=True, help="Path to input XML file")
    ap.add_argument("--xsl", required=True, help="Path to XSL/XSLT stylesheet")
    ap.add_argument("--pdf", required=True, help="Path to output PDF file")
    ap.add_argument("--xhtml-out", default=None, help="Optional: write intermediate XHTML to this file")
    ap.add_argument(
        "--base-dir",
        default=None,
        help="Base directory for resolving relative resources (images/CSS) referenced in XHTML",
    )
    ap.add_argument(
        "--param",
        action="append",
        default=[],
        help="Optional XSLT param in key=value form. Can be repeated.",
    )
    args = ap.parse_args()

    xml_path = Path(args.xml).expanduser().resolve()
    xsl_path = Path(args.xsl).expanduser().resolve()
    pdf_path = Path(args.pdf).expanduser().resolve()

    if not xml_path.exists():
        raise FileNotFoundError(f"XML not found: {xml_path}")
    if not xsl_path.exists():
        raise FileNotFoundError(f"XSLT not found: {xsl_path}")

    xslt_params = parse_kv_params(args.param) if args.param else None

    xhtml = xslt_xml_to_xhtml(xml_path, xsl_path, xslt_params=xslt_params)

    if args.xhtml_out:
        xhtml_out_path = Path(args.xhtml_out).expanduser().resolve()
        xhtml_out_path.parent.mkdir(parents=True, exist_ok=True)
        xhtml_out_path.write_text(xhtml, encoding="utf-8")

    base_dir = Path(args.base_dir).expanduser().resolve() if args.base_dir else xml_path.parent
    xhtml_to_pdf(xhtml, pdf_path, base_dir=base_dir)

    print(f"✅ PDF written to: {pdf_path}")
    if args.xhtml_out:
        print(f"📝 XHTML written to: {Path(args.xhtml_out).expanduser().resolve()}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write(f"ERROR: {e}\n")
        sys.exit(1)
