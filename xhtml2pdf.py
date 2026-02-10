Yep — that WeasyPrint error is not your code. It’s your Linux system library.
What the error means
You have this at the bottom:

undefined symbol: pango_context_set_round_glyph_positions

WeasyPrint calls a function that exists only in newer Pango.
But your machine is loading an older /lib64/libpango-1.0.so.0, so the symbol isn’t there → crash.
So the fix is: use a newer Pango (without changing XML/XSL).

Best fix without sudo: install WeasyPrint + Pango via Conda (in your home directory)
This avoids system packages completely and works on locked-down servers.
Option A) Micromamba (smallest, no sudo)
# 1) Download micromamba into your home dir
curl -L https://micro.mamba.pm/api/micromamba/linux-64/latest -o micromamba.tar.bz2
tar -xjf micromamba.tar.bz2
mkdir -p ~/bin
mv bin/micromamba ~/bin/
export PATH=~/bin:$PATH

# 2) Create env with weasyprint + correct native libs
micromamba create -y -n wp -c conda-forge \
  python=3.10 weasyprint=52.5 pango cairo gdk-pixbuf libffi harfbuzz fontconfig

micromamba activate wp

# 3) Run your script
python convert_weasy.py hcamockedccd.xml HealowStylesheet.xsl output.pdf

If micromamba activate doesn’t work in your shell, do:
eval "$(~/bin/micromamba shell hook -s bash)"
micromamba activate wp

Option B) Miniconda (bigger but common)
Install Miniconda in ~/miniconda3, then:
conda create -y -n wp -c conda-forge \
  python=3.10 weasyprint=52.5 pango cairo gdk-pixbuf libffi harfbuzz fontconfig
conda activate wp
python convert_weasy.py hcamockedccd.xml HealowStylesheet.xsl output.pdf


Quick verify you’re not using the old system Pango
After activating the env:
python -c "import weasyprint; print('weasyprint ok')"
python -c "import ctypes.util; print(ctypes.util.find_library('pango-1.0'))"

You want it to resolve to the conda env, not /lib64/....

If you absolutely can’t use conda/micromamba
Then WeasyPrint won’t run on that machine unless IT upgrades Pango.
In that case, your realistic options are:


Playwright/Chromium HTML→PDF (Chromium is bundled, usually no sudo needed)


keep using xhtml2pdf with aggressive sanitization (but you already saw how brittle it is)



If you tell me what OS this is (Amazon Linux 2? RHEL 7? CentOS 7?), I can tailor the exact micromamba commands and avoid any package mismatches.





--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# XML + XSL to PDF Conversion – Investigation Summary

## Objective

Convert **client-provided XML + XSL** into **PDF** using Python, **without modifying XML or XSL**.

---

## Initial Requirements & Constraints

* XML and XSL are **owned by the client** → cannot change them
* Solution must run in a **restricted Linux environment** (no sudo)
* Prefer a **pure-Python pipeline** if possible

---

## Solution Paths Tried

### 0. XML + XSL → XSL-FO → PDF using **Apache FOP**

**Pipeline**

```
XML + XSL → XSL-FO → PDF (Apache FOP)
```

**Why This Was Tried**

* Apache FOP is the *correct* engine when XSL produces **XSL-FO**
* Very common in healthcare / clinical document pipelines
* Stable, standards-based FO rendering

**Outcome**

* Java-based execution via Apache FOP was tested
* PDF generation worked at a basic level

**Issues Encountered**

* Requires **Java runtime** and FOP binaries
* Harder to embed cleanly into an existing Python-only pipeline
* Operational overhead (managing Java, FOP configs, fonts)
* Environment constraints made long-term maintenance undesirable

**Conclusion**
⚠️ Technically correct for FO, but **operationally heavy** for this setup

---

### 1. XML + XSL → XHTML → PDF using **xhtml2pdf**

**Pipeline**

```
XML + XSL (lxml) → XHTML → PDF (xhtml2pdf)
```

**Outcome**

* XHTML generation via `lxml` works correctly
* PDF generation **fails repeatedly** due to CSS parsing errors

**Errors Observed**

* `NotImplementedType object is not iterable`
* `Invalid color value 'collapse'`
* `invalid literal for int() with base 10: '100%'`

**Root Cause**

* `xhtml2pdf` has **very limited and buggy CSS support**
* Client XSL emits modern / complex CSS such as:

  * `@page` rules
  * `border-collapse: collapse`
  * percentage-based widths (`width: 100%`)

**Mitigations Attempted**

* Python-side XHTML/CSS sanitization:

  * strip `@page`, `@font-face`, `@media`
  * remove `border-collapse`, `%` widths, `position: fixed`
* Aggressive fallback: remove **all CSS**

**Result**

* Even with heavy sanitization, `xhtml2pdf` remains **unstable and brittle**
* Usable PDF generation is **not reliable**

**Conclusion**
❌ `xhtml2pdf` is **not suitable** for this stylesheet

---

### 2. XML + XSL → XHTML → PDF using **WeasyPrint 52.5**

**Pipeline**

```
XML + XSL (lxml) → XHTML → PDF (WeasyPrint)
```

**Why WeasyPrint**

* Modern CSS support
* Proper handling of `@page`, tables, percentages
* Much closer to browser-quality rendering

**Outcome**

* Python code is correct
* Fails at runtime with native library error

**Error Observed**

```
undefined symbol: pango_context_set_round_glyph_positions
```

**Root Cause**

* System has **old Pango (libpango-1.0.so.0)**
* WeasyPrint 52.5 requires **newer Pango**
* Cannot upgrade system libraries without sudo

**Proposed Fix (Not Yet Applied)**

* Install WeasyPrint + Pango via **micromamba / conda** in user space
* This avoids system libraries entirely

**Status**
⚠️ Blocked pending approval / ability to use micromamba or conda

---

### 3. Chromium / Playwright (Discussed, Not Implemented)

**Pipeline**

```
XML + XSL → XHTML → PDF (Headless Chromium)
```

**Pros**

* Full HTML/CSS support
* No dependency on Pango
* Very high rendering fidelity

**Cons**

* Requires Node.js + Chromium runtime
* Heavier than Python-only solutions

**Status**
🟡 Considered as a fallback option

---

## Current Status (Where We Are Stuck)

* ❌ `xhtml2pdf` cannot reliably handle the client’s XHTML/CSS
* ⚠️ WeasyPrint code works but is blocked by **outdated system Pango**
* 🔒 Cannot change XML, XSL, or system libraries

---

## Recommended Next Steps

### Preferred (Cleanest)

✅ Use **micromamba / conda** to run WeasyPrint 52.5 with bundled native libs

### Acceptable Alternative

✅ Use **Playwright / Chromium** for HTML → PDF

### Not Recommended

❌ Further investment in `xhtml2pdf`

---

## Final Recommendation

For long-term stability and correctness **without touching client XSL**:

> **WeasyPrint (via micromamba/conda) or Chromium-based PDF rendering is required.**

Anything else will remain fragile and high-maintenance.
