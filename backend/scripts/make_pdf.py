"""Turn a plain-text resume into a simple text PDF (for demos and tests).

    python -m scripts.make_pdf ../data/eval/resumes/r01.txt ../data/sample_resume.pdf
"""

import re
import sys
import textwrap
from pathlib import Path

import pymupdf

_HANGUL = re.compile(r"[가-힣]")
_TOP, _BOTTOM, _LEFT, _LINE = 60, 790, 50, 13


def text_to_pdf(text: str) -> bytes:
    doc = pymupdf.open()
    page, y = None, _TOP
    for raw in text.splitlines():
        # The built-in CJK font has wide glyphs, so Korean lines wrap earlier.
        korean = bool(_HANGUL.search(raw))
        font, width = ("korea", 48) if korean else ("helv", 95)
        if korean:
            raw = raw.replace("—", "-").replace("–", "-")
        for line in textwrap.wrap(raw, width) or [""]:
            if page is None or y > _BOTTOM:
                page, y = doc.new_page(), _TOP
            page.insert_text((_LEFT, y), line, fontsize=10, fontname=font)
            y += _LINE
    data = doc.tobytes()
    doc.close()
    return data


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    Path(sys.argv[2]).write_bytes(text_to_pdf(Path(sys.argv[1]).read_text(encoding="utf-8")))
    print(f"wrote {sys.argv[2]}")
