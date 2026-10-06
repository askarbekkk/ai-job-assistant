import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { ErrorBox, JobBadges, ScoreRing, SkillChips } from "../components/common.jsx";

export default function JobDetailPage() {
  const { jobId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [match, setMatch] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.job(jobId).then(setJob).catch(setError);
    if (user) api.matchForJob(jobId).then(setMatch).catch(() => setMatch(null));
  }, [jobId, user]);

  async function toggleSave() {
    await (match.saved ? api.unsave(jobId) : api.save(jobId));
    setMatch({ ...match, saved: !match.saved });
  }

  if (error) return <ErrorBox error={error} />;
  if (!job) return <p className="muted">Loading…</p>;

  return (
    <div className="stack">
      <button className="link-btn muted small" onClick={() => navigate(-1)}>
        ← Back
      </button>
      <section className="card">
        <div className="job-head">
          <div>
            <h1>{job.title}</h1>
            <div className="muted">{job.company}</div>
          </div>
          <JobBadges job={job} />
        </div>

        {match && (
          <div className="match-box">
            <ScoreRing score={match.score} />
            <div className="match-detail">
              <div className="breakdown small">
                Skill overlap {Math.round(match.skill_overlap * 100)}% · Text similarity{" "}
                {match.text_similarity.toFixed(2)}
              </div>
              <div className="skill-row">
                <span className="label">You have</span>
                <SkillChips skills={match.matched_skills} kind="have" />
              </div>
              <div className="skill-row">
                <span className="label">Missing</span>
                <SkillChips skills={match.missing_skills} kind="missing" empty="Nothing missing" />
              </div>
            </div>
            <button className={`btn ${match.saved ? "btn-saved" : ""}`} onClick={toggleSave}>
              {match.saved ? "★ Saved" : "☆ Save"}
            </button>
          </div>
        )}
        {user && !match && (
          <p className="muted small">
            <Link to="/resume">Upload your resume</Link> to see your match score for this posting.
          </p>
        )}

        <div className="skill-row">
          <span className="label">Required</span>
          <SkillChips skills={job.required_skills} />
        </div>
        <div className="skill-row">
          <span className="label">Preferred</span>
          <SkillChips skills={job.preferred_skills} kind="preferred" />
        </div>

        <h3>Description</h3>
        <p className="description">{job.description}</p>
        <p className="muted small">
          Collected {job.collected_date ?? "—"} · this is a snapshot, the original posting may have expired.{" "}
          {job.source_url && (
            <a href={job.source_url} target="_blank" rel="noreferrer">
              Original posting ↗
            </a>
          )}
        </p>
      </section>
    </div>
  );
}
