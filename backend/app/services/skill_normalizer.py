"""Module 2 — Skill Normalizer.

Maps different spellings to one standard name using the team-made skill list
in data/skills.json (e.g. "ML" -> "Machine Learning", "파이썬" -> "Python").

Each entry in skills.json:
    {"name": "Machine Learning", "category": "AI/ML",
     "aliases": ["ml", "머신러닝"],
     "keyword_exclude": ["ml"]}          # optional

`aliases` are used both to normalize LLM output and to find skills in raw text
(keyword extraction). Aliases listed in `keyword_exclude` are too ambiguous to
search for in free text ("Go", "R", "CV", "TS") and are only used to normalize.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

from ..config import settings

_SEPARATORS = re.compile(r"[\s\-_]+")


def _key(text: str) -> str:
    return _SEPARATORS.sub(" ", text.strip().lower()).strip()


def _keyword_pattern(term: str) -> re.Pattern:
    parts = [re.escape(p) for p in _SEPARATORS.split(term.strip()) if p]
    body = r"[\s\-_]+".join(parts)
    # Latin letters/digits may not touch the term (so "Java" does not match
    # "JavaScript" and "SQL" does not match "MySQL"), but Korean particles may
    # follow it ("파이썬을").
    return re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9+#])", re.IGNORECASE)


class SkillNormalizer:
    def __init__(self, entries: list[dict]):
        self.names: list[str] = []
        self.categories: dict[str, str] = {}
        self._canonical: dict[str, str] = {}
        self._patterns: list[tuple[str, re.Pattern]] = []

        for entry in entries:
            name = entry["name"]
            self.names.append(name)
            self.categories[name] = entry.get("category", "Other")
            excluded = {_key(a) for a in entry.get("keyword_exclude", [])}
            for term in [name, *entry.get("aliases", [])]:
                self._canonical[_key(term)] = name
                if _key(term) not in excluded:
                    self._patterns.append((name, _keyword_pattern(term)))

    @classmethod
    def from_file(cls, path: Path) -> "SkillNormalizer":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data["skills"])

    def is_known(self, skill: str) -> bool:
        return _key(skill) in self._canonical

    def normalize(self, raw: str) -> str | None:
        """Return the standard name; unknown skills are kept as typed (trimmed)."""
        cleaned = " ".join(str(raw).split()).strip(" .,;:")
        if not cleaned or len(cleaned) > 60:
            return None
        return self._canonical.get(_key(cleaned), cleaned)

    def normalize_many(self, raws: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for raw in raws:
            name = self.normalize(raw)
            if name and name.lower() not in seen:
                seen.add(name.lower())
                result.append(name)
        return result

    def extract_keywords(self, text: str) -> list[str]:
        """Find known skills mentioned in free text (no LLM)."""
        found: list[str] = []
        seen: set[str] = set()
        for name, pattern in self._patterns:
            if name not in seen and pattern.search(text):
                seen.add(name)
                found.append(name)
        return found

    def search(self, query: str, limit: int = 20) -> list[str]:
        q = _key(query)
        if not q:
            return self.names[:limit]
        starts = [n for n in self.names if _key(n).startswith(q)]
        contains = [n for n in self.names if q in _key(n) and n not in starts]
        return (starts + contains)[:limit]


@lru_cache
def get_normalizer() -> SkillNormalizer:
    return SkillNormalizer.from_file(settings.skills_file)
