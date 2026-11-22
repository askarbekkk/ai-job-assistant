"""TOPIK requirement read from posting text, and the skill what-if."""

from types import SimpleNamespace

from app.services.korean import topik_requirement
from app.services.matching import JobMatch, skill_boosts


def test_topik_from_text():
    assert topik_requirement("자격요건: TOPIK 4급 이상") == (4, True)
    assert topik_requirement("Requirements: TOPIK level 5 or higher") == (5, True)
    assert topik_requirement("한국어능력시험 3급 이상 우대") == (3, True)
    assert topik_requirement("ㆍ한국어능력시험(TOPIK) 4~6급 보유자") == (4, True)  # LG Innotek global internship
    assert topik_requirement("Korean is not required; English team") == (0, True)
    assert topik_requirement("Business Korean preferred", "Basic") == (5, False)
    assert topik_requirement("Conversational Korean is a plus", "Basic") == (3, False)
    # Nothing said: estimated from the posting's language.
    assert topik_requirement("데이터 분석 업무", "Fluent") == (5, False)
    assert topik_requirement("We build LLM apps", "None") == (0, False)
    assert topik_requirement("Python 3년 이상") == (5, False)  # "3년" is years, not a TOPIK level


def _m(job_id, matched, missing, sim=0.1):
    job = SimpleNamespace(job_id=job_id, title=job_id, company="c")
    score = round(100 * (0.7 * len(matched) / (len(matched) + len(missing)) + 0.3 * sim), 1)
    return JobMatch(job, score, 0, sim, matched, missing, [])


def test_skill_boosts_rank_by_postings_unlocked():
    matches = [
        _m("a", ["Python", "SQL"], ["Docker"]),  # 49.7 -> 73.0 with Docker: unlocked
        _m("b", ["Python"], ["Docker"]),  # 38.0 -> 73.0: unlocked
        _m("c", ["Python"], ["Kubernetes", "Go", "Rust"]),  # one skill helps only a little
        _m("d", ["Python"], ["Communication"]),  # soft skills are not suggested
    ]
    boosts = skill_boosts(matches)
    assert "Communication" not in [b.skill for b in boosts]
    assert boosts[0].skill == "Docker" and boosts[0].unlocked == 2 and boosts[0].improved == 2
    job, now, after = boosts[0].jobs[0]
    assert now < 70 <= after
