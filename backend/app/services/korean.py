"""How much Korean a posting needs, as a TOPIK level (0 = not required, 1-6).

Returns (level, stated): `stated` is True only when the posting itself says it —
an explicit TOPIK level ("TOPIK 4급 이상") or "Korean not required". Everything
else is an estimate from wording ("business Korean") or from the posting's
language (a posting written in Korean expects Korean at work).
"""

import re

_TOPIK = re.compile(
    r"(?:TOPIK|토픽|한국어\s*능력\s*시험)\s*(?:\(\s*TOPIK\s*\))?\s*(?:level|레벨)?\s*([1-6])(?!\d)"
    r"|([1-6])\s*급\s*(?:이상\s*)?\(?\s*(?:TOPIK|토픽)",
    re.IGNORECASE,
)
_NOT_REQUIRED = re.compile(
    r"korean\s+(?:is\s+)?not\s+(?:required|necessary|needed)|no\s+korean\s+(?:required|needed)"
    r"|without\s+korean|한국어\s*(?:불필요|무관|필수\s*아님)",
    re.IGNORECASE,
)
_FLUENT = re.compile(
    r"(?:business|fluent|native|advanced)[\s-]+(?:level\s+)?korean|korean\s*\((?:fluent|native|business)"
    r"|한국어\s*(?:능통|원어민|비즈니스|유창)",
    re.IGNORECASE,
)
_BASIC = re.compile(
    r"(?:basic|conversational|intermediate)[\s-]+(?:level\s+)?korean|한국어\s*(?:기초|일상\s*회화|가능자)",
    re.IGNORECASE,
)


def topik_requirement(description: str, korean_required: str = "") -> tuple[int, bool]:
    levels = [int(a or b) for a, b in _TOPIK.findall(description)]
    if levels:
        return min(levels), True
    if _NOT_REQUIRED.search(description):
        return 0, True
    if _FLUENT.search(description):
        return 5, False
    if _BASIC.search(description):
        return 3, False
    return {"None": 0, "Basic": 3}.get(korean_required, 5), False
