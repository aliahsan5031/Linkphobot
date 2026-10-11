"""Rebuild linkphobot/assets/fonts/*.b64 from the original font files.

Hugging Face Spaces reject binary files in a plain git push, so the fonts are
stored as text: subset to Latin, Greek and Cyrillic, compressed, base64-encoded.

Usage (needs ``pip install fonttools``):
    python scripts/pack_fonts.py /path/to/Inter-Regular.otf /path/to/Poppins-Bold.ttf ...
"""

import base64
import io
import sys
import textwrap
import zlib
from pathlib import Path

from fontTools import subset

UNICODES = (
    "U+0020-007E,U+00A0-024F,U+0370-03FF,U+0400-04FF,U+2010-2027,U+2030-203A,U+2044,"
    "U+20A0-20CF,U+2122,U+2190-2193,U+2212,U+2260,U+2264,U+2265,U+2248,U+221E,U+00D7"
)
OUT = Path(__file__).resolve().parent.parent / "linkphobot" / "assets" / "fonts"


def pack(path: Path) -> None:
    options = subset.Options()
    options.layout_features = ["kern"]
    options.hinting = False
    options.desubroutinize = True
    font = subset.load_font(str(path), options)
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=subset.parse_unicodes(UNICODES))
    subsetter.subset(font)
    buffer = io.BytesIO()
    subset.save_font(font, buffer, options)
    encoded = base64.b64encode(zlib.compress(buffer.getvalue(), 9)).decode()
    target = OUT / f"{path.stem}.b64"
    target.write_text("\n".join(textwrap.wrap(encoded, 100)) + "\n")
    print(f"{target.name}: {target.stat().st_size // 1024} KB")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        pack(Path(arg))
