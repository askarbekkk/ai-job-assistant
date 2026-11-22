import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import {
  ErrorBox,
  FilterBar,
  Icon,
  JobCard,
  ScoreRing,
  SkeletonCards,
  SkillChips,
  useCountUp,
  useFilters,
} from "../components/common.jsx";
import { useT } from "../i18n.jsx";

export default function RecommendationsPage() {
  const { t } = useT();
  const [filters, setFilters] = useFilters();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .recommendations(filters)
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [filters, reload]);

  async function toggleSave(match) {
    const id = match.job.job_id;
    await (match.saved ? api.unsave(id) : api.save(id));
    setData((d) => ({
      ...d,
      results: d.results.map((m) => (m.job.job_id === id ? { ...m, saved: !m.saved } : m)),
    }));
  }

  /** "I already have it": add the skill to the resume and score everything again. */
  async function addSkill(skill) {
    const resume = await api.getResume();
    await api.updateSkills([...resume.skills, skill]);
    setReload((n) => n + 1);
  }

  if (error?.status === 400) {
    return (
      <div className="card empty">
        <h2>{t("Upload your resume first")}</h2>
        <p className="muted">{t("We need your skills to recommend postings.")}</p>
        <Link to="/resume" className="btn btn-primary">
          {t("Upload resume")}
        </Link>
      </div>
    );
  }

  const live = data?.results.filter((m) => /wanted|jobkorea|jumpit/i.test(m.job.source_url)).length ?? 0;

  return (
    <div className="stack">
      <section className="page-head">
        <div>
          <span className="eyebrow">{t("Your top {n}", { n: data?.results.length || 10 })}</span>
          <h1>{t("Matches for you")}</h1>
        </div>
        <div className="stats">
          <Stat label={t("best score")} value={data?.results[0]?.score ?? 0} />
          <Stat label={t("postings checked")} value={data?.total_candidates ?? 0} />
          <Stat label={t("live in top list")} value={live} />
        </div>
      </section>
      <FilterBar filters={filters} onChange={setFilters} />
      <ErrorBox error={error} />

      <div className="two-col">
        <div className="stack">
          {loading && <SkeletonCards count={4} />}
          {!loading && data?.results.length === 0 && (
            <div className="card empty">{t("No postings match these filters. Try widening them.")}</div>
          )}
          {!loading &&
            data?.results.map((m, i) => (
              <MatchCard key={m.job.job_id} rank={i + 1} match={m} onToggleSave={() => toggleSave(m)} />
            ))}
        </div>

        {data && (
          <aside className="stack">
            <SkillBoosts boosts={data.skill_boosts} onAdd={addSkill} />
            <div className="card small muted">
              <strong>{t("How the score works")}</strong>
              <p>
                {t(
                  "Match = 100 × ({ws} × skill overlap + {wt} × text similarity). Skill overlap is the share of the posting's required skills that you have; text similarity compares your resume with the posting text ({backend}).",
                  {
                    ws: data.weights.skill,
                    wt: data.weights.text,
                    backend: data.similarity_backend === "sbert" ? "Sentence-BERT" : "TF-IDF",
                  }
                )}
              </p>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  const shown = useCountUp(value);
  return (
    <div className="stat">
      <strong>{Math.round(shown)}</strong>
      <span>{label}</span>
    </div>
  );
}

function MatchCard({ rank, match, onToggleSave }) {
  const { t } = useT();
  const total = match.matched_skills.length + match.missing_skills.length;
  return (
    <JobCard job={match.job} index={rank - 1}>
      <div className="match-body">
        <div className="match-score">
          <span className="rank">#{rank}</span>
          <ScoreRing score={match.score} />
        </div>
        <div className="match-detail">
          <div className="breakdown small">
            {t("Skills {have}/{total} ({pct}%) · Text similarity {sim}", {
              have: match.matched_skills.length,
              total,
              pct: Math.round(match.skill_overlap * 100),
              sim: match.text_similarity.toFixed(2),
            })}
          </div>
          <div className="skill-row">
            <span className="label">{t("You have")}</span>
            <SkillChips skills={match.matched_skills} kind="have" />
          </div>
          <div className="skill-row">
            <span className="label">{t("Missing")}</span>
            <SkillChips skills={match.missing_skills} kind="missing" empty={t("Nothing — you have all required skills")} />
          </div>
          {match.missing_preferred.length > 0 && (
            <div className="skill-row">
              <span className="label">{t("Nice to have")}</span>
              <SkillChips skills={match.missing_preferred} kind="preferred" />
            </div>
          )}
        </div>
        <button className={`btn ${match.saved ? "btn-saved" : ""}`} onClick={onToggleSave}>
          {t(match.saved ? "★ Saved" : "☆ Save")}
        </button>
      </div>
    </JobCard>
  );
}

/** What-if per missing skill: which postings would fit better if the user had it. */
function SkillBoosts({ boosts, onAdd }) {
  const { t } = useT();
  const [open, setOpen] = useState(boosts[0]?.skill ?? null);
  const [adding, setAdding] = useState(null);

  return (
    <div className="card boosts">
      <h3>{t("Grow your matches")}</h3>
      <p className="muted small">
        {t("Add one skill and see which postings would fit you better.")} {t("Strong match = score 70+.")}
      </p>
      {boosts.length === 0 ? (
        <p className="muted">{t("No suggestions: you already cover the required skills of these postings.")}</p>
      ) : (
        <ul className="boost-list">
          {boosts.map((b, i) => {
            const isOpen = open === b.skill;
            return (
              <li key={b.skill} className={`boost reveal ${isOpen ? "open" : ""}`} style={{ "--i": i }}>
                <button className="boost-head" aria-expanded={isOpen} onClick={() => setOpen(isOpen ? null : b.skill)}>
                  <span className="boost-skill">
                    <Icon name="plus" /> {b.skill}
                  </span>
                  <span className={`boost-gain ${b.unlocked ? "strong" : ""}`}>
                    {b.unlocked
                      ? t(b.unlocked === 1 ? "+1 strong match" : "+{n} strong matches", { n: b.unlocked })
                      : t(b.improved === 1 ? "1 posting scores higher" : "{n} postings score higher", { n: b.improved })}
                  </span>
                  <span className="boost-chev">
                    <Icon name="chevron" />
                  </span>
                </button>
                {isOpen && (
                  <div className="boost-body">
                    <ul>
                      {b.jobs.map((j) => (
                        <li key={j.job_id}>
                          <Link to={`/jobs/${j.job_id}`} className="boost-job">
                            <span className="boost-title">{j.title}</span>
                            <span className="muted small">{j.company}</span>
                          </Link>
                          <span className="score-move">
                            <span>{Math.round(j.score_now)}</span>
                            <Icon name="arrow" />
                            <strong className={j.score_with_skill >= 70 ? "good" : ""}>{Math.round(j.score_with_skill)}</strong>
                          </span>
                        </li>
                      ))}
                    </ul>
                    <button
                      className="btn btn-small"
                      disabled={adding === b.skill}
                      onClick={async () => {
                        setAdding(b.skill);
                        try {
                          await onAdd(b.skill);
                        } finally {
                          setAdding(null);
                        }
                      }}
                    >
                      {adding === b.skill ? t("Adding…") : t("I already have it")}
                    </button>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
