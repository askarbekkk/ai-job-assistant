"""Live job search: after a resume upload, find current postings on Korean job sites.

The resume's skills become web searches (Tavily API) on Wanted, Jumpit and JobKorea.
Each result that is a real posting page is parsed (company, title, type, location,
Korean level), its skills are extracted with the keyword extractor, and it is
upserted into `jobs`, so the normal matching engine ranks it with everything else.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..crud import set_job_skills
from ..models import Job
from .extraction import keyword_job

log = logging.getLogger(__name__)

TAVILY_URL = "https://api.tavily.com/search"

# Posting pages only (search and list pages are skipped). (site prefix, url regex)
POSTING_URLS = [
    ("W", re.compile(r"wanted\.co\.kr/wd/(\d+)")),
    ("JP", re.compile(r"jumpit\.saramin\.co\.kr/position/(\d+)")),
    ("JK", re.compile(r"jobkorea\.co\.kr/Recruit/GI_Read/(\d+)", re.I)),
]
SITE_NAMES = {"W": "Wanted", "JP": "Jumpit", "JK": "JobKorea"}

ROLES = [  # first matching skill group decides what kind of job to search for
    ({"machine learning", "deep learning", "pytorch", "tensorflow", "nlp", "llm", "computer vision", "rag"}, "AI 엔지니어"),
    ({"pandas", "data analysis", "sql", "tableau", "power bi", "statistics"}, "데이터 분석"),
    ({"react", "javascript", "typescript", "vue.js", "next.js"}, "프론트엔드 개발자"),
    ({"java", "spring", "node.js", "fastapi", "django", "nestjs"}, "백엔드 개발자"),
]

CITIES = [
    ("Seoul", ("서울", "seoul", "강남", "gangnam")),
    ("Seongnam", ("판교", "성남", "pangyo", "seongnam", "분당")),
    ("Daejeon", ("대전", "daejeon")),
    ("Busan", ("부산", "busan")),
    ("Incheon", ("인천", "incheon")),
    ("Suwon", ("수원", "suwon")),
    ("Ulsan", ("울산", "ulsan")),
    ("Jeju", ("제주", "jeju")),
    ("Remote", ("재택", "remote", "원격")),
]


def enabled() -> bool:
    return bool(settings.tavily_api_key)


def build_queries(skills: list[str]) -> list[tuple[str, list[str]]]:
    lower = {s.lower() for s in skills}
    role = next((r for group, r in ROLES if lower & group), "개발자")
    # Search with the most specific skills: skip generic ones that match every posting.
    generic = {"git", "english", "korean", "communication", "teamwork", "linux", "microsoft office"}
    top = " ".join([s for s in skills if s.lower() not in generic][:3])
    return [
        (f"{role} 인턴 {top} 채용", ["wanted.co.kr"]),
        (f"{role} 신입 {top} 채용", ["wanted.co.kr"]),
        (f"{role} {top} 채용", ["jumpit.saramin.co.kr", "jobkorea.co.kr"]),
    ]


def _search(query: str, domains: list[str]) -> list[dict]:
    try:
        r = httpx.post(TAVILY_URL, timeout=40, json={
            "api_key": settings.tavily_api_key, "query": query, "max_results": 10,
            "include_domains": domains, "include_raw_content": True,
        })
        r.raise_for_status()
        return r.json().get("results", [])
    except Exception:
        log.warning("Tavily search failed: %s", query, exc_info=True)
        return []


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("(주)", "").replace("㈜", "").replace("주식회사", "")).strip(" -|")


def parse_title(prefix: str, title: str) -> tuple[str, str]:
    """(company, job title) from the page title each site uses."""
    if prefix == "W":  # "[루모스] AI/ML 엔지니어 채용 공고 | 원티드"
        m = re.match(r"\[(.+?)\]\s*(.+?)\s*채용 공고", title)
        if m:
            return _clean(m[1]), _clean(m[2])
    if prefix == "JK":
        title = re.sub(r"\s*[-|–—]\s*잡코리아\s*$", "", title)
        m = re.match(r"(.+?) 채용 - (.+)$", title)  # "파워인포텍 채용 - LLM 엔지니어"
        if m:
            return _clean(m[1]), _clean(m[2])
        m = re.match(r"(.+) - (.+?) 채용$", title)  # "데이터 분석가 - 더블유게임즈 채용"
        if m:
            return _clean(m[2]), _clean(m[1])
    if prefix == "JP":  # "점핏 | AI 엔지니어 채용" or "[캐시워크] 데이터분석 - 점핏"
        title = _clean(re.sub(r"^점핏\s*\||-\s*점핏$", "", title))
    m = re.match(r"\[(.+?)\]\s*(.+)", title)
    if m:
        return _clean(m[1]), _clean(m[2])
    return f"via {SITE_NAMES[prefix]}", _clean(title)


def is_entry_level(title: str) -> bool:
    """Interns and new grads only: drop postings that ask for 3+ years or say 경력 only."""
    if re.search(r"인턴|신입|주니어|intern|junior|new grad", title, re.I):
        return True
    years = [int(n) for n in re.findall(r"(\d+)\s*년", title)]
    senior = re.search(r"경력|시니어|senior|middle|lead|팀장|리드", title, re.I)
    return not senior and not any(n >= 3 for n in years)


def guess_location(text: str) -> str:
    low = text.lower()
    # ponytail: first city named on the page wins; a posting's "related jobs" sidebar can mislead it.
    hits = [(low.find(w), city) for city, words in CITIES for w in words if w in low]
    return min(hits)[1] if hits else "Seoul"


def guess_korean(text: str) -> str:
    letters = re.findall(r"[A-Za-z가-힣]", text)
    hangul = sum("가" <= c <= "힣" for c in letters)
    if letters and hangul / len(letters) > 0.3:
        return "Fluent"  # a posting written in Korean expects Korean at work
    return "None" if re.search(r"korean (is )?not required|no korean", text, re.I) else "Basic"


def to_job_row(result: dict) -> dict | None:
    url = result.get("url", "")
    for prefix, rx in POSTING_URLS:
        m = rx.search(url)
        if m:
            break
    else:
        return None
    page_title = result.get("title", "")
    company, title = parse_title(prefix, page_title)
    text = (result.get("raw_content") or result.get("content") or "")[:6000]
    if not title or not text or not is_entry_level(page_title):
        return None
    return {
        "job_id": f"{prefix}{m[1]}"[:20],
        "company": company[:200],
        "title": title[:300],
        "employment_type": "Internship" if re.search(r"인턴|intern", title, re.I) else "Full-time",
        "location": guess_location(text),
        "korean_required": guess_korean(text),
        "description": text,
        "source_url": url.split("?")[0],
    }


def find_postings(skills: list[str]) -> list[dict]:
    """Web search for postings matching `skills`, as job rows (not yet stored)."""
    queries = build_queries(skills)
    with ThreadPoolExecutor(len(queries)) as pool:
        results = [r for batch in pool.map(lambda q: _search(*q), queries) for r in batch]
    return [row for row in map(to_job_row, results) if row]


def search_and_store(db: Session, skills: list[str]) -> int:
    """Search the web for postings matching `skills` and upsert them. Returns how many were found
    (already-known postings count too: they are confirmed as still listed today)."""
    if not enabled() or not skills:
        return 0

    # Sites re-post the same job under new ids, so (company, title) is the identity.
    same = lambda company, title: f"{company}|{title}".lower()  # noqa: E731
    known = {same(c, t): i for i, c, t in db.query(Job.job_id, Job.company, Job.title)}
    rows = {}
    for row in find_postings(skills):
        key = same(row["company"], row["title"])
        row["job_id"] = known.get(key, row["job_id"])
        if key not in rows:
            rows[key] = row

    new = 0
    for row in rows.values():
        job = db.get(Job, row["job_id"])
        if job is None:
            job = Job(**row)
            db.add(job)
            new += 1
            skills_found = keyword_job(row["description"])
            set_job_skills(db, job, skills_found.required, skills_found.preferred)
        job.collected_date = date.today()
    db.commit()
    log.info("Live search: %d postings found, %d new", len(rows), new)
    return len(rows)
