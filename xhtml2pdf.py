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
