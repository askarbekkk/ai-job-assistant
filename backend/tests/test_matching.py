"""Unit tests for the normalizer, matching formula and import cleaning."""

from types import SimpleNamespace

from app.services.extraction import keyword_job
from app.services.matching import Filters, compare_skills, final_score, passes_filters, score_jobs
from app.services.similarity import tfidf_similarities
from app.services.skill_normalizer import get_normalizer
from scripts.import_jobs import Report, clean_rows


def _job(job_id="J1", required=(), preferred=(), **kw):
    defaults = dict(location="Seoul", employment_type="Internship", korean_required="None")
    defaults.update(kw)
    return SimpleNamespace(job_id=job_id, required_skills=list(required), preferred_skills=list(preferred), **defaults)


def test_proposal_example_scores_70_5():
    """Section 10 example: overlap 3/4, similarity 0.60 -> 70.5, missing Tableau."""
    cmp = compare_skills(["Python", "SQL", "Pandas"], ["Python", "SQL", "Pandas", "Tableau"])
    assert cmp.overlap == 0.75
    assert cmp.missing == ["Tableau"]
    assert final_score(cmp.overlap, 0.60, 0.7, 0.3) == 70.5


def test_skill_comparison_is_case_insensitive_and_uses_preferred_when_no_required():
    assert compare_skills(["python"], ["Python"]).overlap == 1.0
    cmp = compare_skills(["Docker"], [], ["Docker", "Kubernetes"])
    assert cmp.overlap == 0.5 and cmp.missing == ["Kubernetes"]
    assert compare_skills(["Docker"], []).overlap == 0.0


def test_filters():
    job = _job(location="Daejeon", employment_type="Full-time", korean_required="Basic")
    assert passes_filters(job, Filters())
    assert passes_filters(job, Filters(location="daejeon", employment_type="full-time"))
    assert not passes_filters(job, Filters(location="Seoul"))
    assert not passes_filters(job, Filters(korean_level="None"))
    assert passes_filters(job, Filters(korean_level="Basic"))
    assert passes_filters(job, Filters(korean_level="Fluent"))


def test_ranking_order():
    jobs = [_job("A", ["Python", "SQL"]), _job("B", ["Java"]), _job("C", ["Python", "Java"])]
    ranked = score_jobs(["Python", "SQL"], jobs, [0.1, 0.1, 0.1], 0.7, 0.3)
    assert [m.job.job_id for m in ranked] == ["A", "C", "B"]


def test_normalizer_aliases():
    n = get_normalizer()
    assert n.normalize("ML") == "Machine Learning"
    assert n.normalize("react.js") == "React"
    assert n.normalize("Scikit Learn") == "scikit-learn"
    assert n.normalize("머신러닝") == "Machine Learning"
    assert n.normalize("golang") == "Go"
    assert n.normalize("  Some Tool ") == "Some Tool"
    assert n.normalize_many(["Python", "python3", "PYTHON"]) == ["Python"]


def test_keyword_extraction_boundaries():
    n = get_normalizer()
    found = set(n.extract_keywords("Skills: JavaScript, MySQL, C++ and 파이썬을 활용한 데이터 분석"))
    assert {"JavaScript", "MySQL", "C++", "Python", "Data Analysis"} <= found
    assert "Java" not in found  # not inside "JavaScript"
    assert "SQL" not in found  # not inside "MySQL"
    assert "C" not in found
    assert "Go" not in n.extract_keywords("Let's go to the next step")


def test_keyword_job_splits_preferred_section():
    r = keyword_job("Requirements: Java, MySQL.\nPreferred: Docker, Java.")
    assert r.required == ["Java", "MySQL"] and r.preferred == ["Docker"]
    r = keyword_job("자격요건: Python, SQL\n우대사항: Tableau")
    assert r.required == ["Python", "SQL"] and r.preferred == ["Tableau"]


def test_tfidf_similarity_prefers_related_text():
    sims = tfidf_similarities("python pandas data analysis", ["data analysis with python and pandas", "ios swift app"])
    assert sims[0] > sims[1] >= 0


def test_import_cleaning():
    base = dict(company="A", title="T", employment_type="intern", location="Seoul",
                korean_required="TOPIK 5", description="Python", source_url="https://x/1", collected_date="2026.10.15")
    rows = [
        {**base, "job_id": "J0001"},
        {**base, "job_id": "J0002"},  # same URL -> duplicate
        {**base, "job_id": "", "source_url": "https://x/2", "korean_required": "maybe"},  # invalid level
        {**base, "job_id": "", "source_url": "https://x/3", "location": ""},
    ]
    report = Report()
    clean = clean_rows(rows, report)
    assert [r["job_id"] for r in clean] == ["J0001", "J0002"]  # new id assigned to the last row
    assert clean[0]["employment_type"] == "Internship" and clean[0]["korean_required"] == "Fluent"
    assert str(clean[0]["collected_date"]) == "2026-10-15"
    assert clean[1]["location"] == "Unknown"
    assert len(report.duplicates) == 1 and len(report.errors) == 1
