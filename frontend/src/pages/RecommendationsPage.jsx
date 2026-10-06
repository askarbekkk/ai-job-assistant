import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { ErrorBox, FilterBar, JobCard, ScoreRing, SkillChips, useFilters } from "../components/common.jsx";

export default function RecommendationsPage() {
  const [filters, setFilters] = useFilters();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .recommendations(filters)
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  }, [filters]);

  async function toggleSave(match) {
    const id = match.job.job_id;
    await (match.saved ? api.unsave(id) : api.save(id));
    setData((d) => ({
      ...d,
      results: d.results.map((m) => (m.job.job_id === id ? { ...m, saved: !m.saved } : m)),
    }));
  }

  if (error?.status === 400) {
    return (
      <div className="card empty">
        <h2>Upload your resume first</h2>
        <p className="muted">We need your skills to recommend postings.</p>
        <Link to="/resume" className="btn btn-primary">
          Upload resume
        </Link>
      </div>
    );
  }

  return (
    <div className="stack">
      <div className="row-between">
        <h1>Top matches for you</h1>
        {data && (
          <span className="muted small">
            {data.total_candidates} postings after filters · {data.elapsed_ms} ms
          </span>
        )}
      </div>
      <FilterBar filters={filters} onChange={setFilters} />
      <ErrorBox error={error} />

      <div className="two-col">
        <div className="stack">
          {loading && <p className="muted">Calculating matches…</p>}
          {!loading && data?.results.length === 0 && (
            <div className="card empty">No postings match these filters. Try widening them.</div>
          )}
          {!loading &&
            data?.results.map((m, i) => (
              <MatchCard key={m.job.job_id} rank={i + 1} match={m} onToggleSave={() => toggleSave(m)} />
            ))}
        </div>

        {data && (
          <aside className="stack">
            <SkillGap items={data.skill_gap} total={data.results.length} />
            <div className="card small muted">
              <strong>How the score works</strong>
              <p>
                Match = 100 × ({data.weights.skill} × skill overlap + {data.weights.text} × text similarity).
                Skill overlap is the share of the posting's required skills that you have; text similarity compares
                your resume with the posting text ({data.similarity_backend === "sbert" ? "Sentence-BERT" : "TF-IDF"}).
              </p>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

function MatchCard({ rank, match, onToggleSave }) {
  const total = match.matched_skills.length + match.missing_skills.length;
  return (
    <JobCard job={match.job}>
      <div className="match-body">
        <div className="match-score">
          <span className="rank">#{rank}</span>
          <ScoreRing score={match.score} />
        </div>
        <div className="match-detail">
          <div className="breakdown small">
            Skills {match.matched_skills.length}/{total} ({Math.round(match.skill_overlap * 100)}%) · Text similarity{" "}
            {match.text_similarity.toFixed(2)}
          </div>
          <div className="skill-row">
            <span className="label">You have</span>
            <SkillChips skills={match.matched_skills} kind="have" />
          </div>
          <div className="skill-row">
            <span className="label">Missing</span>
            <SkillChips skills={match.missing_skills} kind="missing" empty="Nothing — you have all required skills" />
          </div>
          {match.missing_preferred.length > 0 && (
            <div className="skill-row">
              <span className="label">Nice to have</span>
              <SkillChips skills={match.missing_preferred} kind="preferred" />
            </div>
          )}
        </div>
        <button className={`btn ${match.saved ? "btn-saved" : ""}`} onClick={onToggleSave}>
          {match.saved ? "★ Saved" : "☆ Save"}
        </button>
      </div>
    </JobCard>
  );
}

function SkillGap({ items, total }) {
  const max = Math.max(1, ...items.map((i) => i.count));
  return (
    <div className="card">
      <h3>Skills to learn next</h3>
      <p className="muted small">Most frequently missing across your top {total} matches.</p>
      {items.length === 0 ? (
        <p className="muted">No gaps — great fit!</p>
      ) : (
        <ul className="gap-list">
          {items.map((i) => (
            <li key={i.skill}>
              <span>{i.skill}</span>
              <span className="bar">
                <span style={{ width: `${(i.count / max) * 100}%` }} />
              </span>
              <span className="muted small">{i.count}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
