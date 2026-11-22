"""Live job search: parsing of search results (no network)."""

from app.services.live_jobs import build_queries, guess_korean, to_job_row


def test_wanted_posting_is_parsed():
    row = to_job_row({
        "url": "https://www.wanted.co.kr/wd/283066?utm=x",
        "title": "[피카부랩스] [인턴] AI 엔지니어 채용 공고 - 원티드",
        "raw_content": "근무지역 서울 강남구. 자격요건: Python, PyTorch. 우대사항: Docker",
    })
    assert row["job_id"] == "W283066"
    assert (row["company"], row["title"]) == ("피카부랩스", "[인턴] AI 엔지니어")
    assert row["employment_type"] == "Internship"
    assert row["location"] == "Seoul"
    assert row["korean_required"] == "Fluent"
    assert row["source_url"] == "https://www.wanted.co.kr/wd/283066"


def test_jobkorea_posting_and_non_posting_pages():
    row = to_job_row({
        "url": "https://www.jobkorea.co.kr/Recruit/GI_Read/50381653?Oem_Code=C1",
        "title": "㈜파워인포텍 채용 - LLM 엔지니어 (Python / RAG) | 잡코리아",
        "content": "Office in Pangyo. Python, RAG. Korean not required.",
    })
    assert (row["job_id"], row["company"], row["location"]) == ("JK50381653", "파워인포텍", "Seongnam")
    assert row["korean_required"] == "None"
    # Search/list pages are not postings.
    assert to_job_row({"url": "https://www.jobkorea.co.kr/Search?stext=llm", "title": "x", "content": "y"}) is None


def test_only_entry_level_postings():
    row = lambda title: to_job_row({"url": "https://jumpit.saramin.co.kr/position/1", "title": title, "content": "SQL"})  # noqa: E731
    assert row("[캐시워크] 데이터분석 (신입) - 점핏")["company"] == "캐시워크"
    assert row("점핏 | 데이터분석가 경력(11~13년) 채용") is None
    assert row("점핏 | 데이터 사이언티스트 (5년 이상)") is None
    assert row("점핏 | [사람인] 데이터 엔지니어 (전환형인턴)")["employment_type"] == "Internship"


def test_queries_follow_resume_skills():
    assert build_queries(["Git", "React", "TypeScript"])[0][0].startswith("프론트엔드 개발자 인턴 React TypeScript")
    assert guess_korean("We build LLM apps in English") == "Basic"
