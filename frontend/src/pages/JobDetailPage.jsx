import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { ErrorBox, JobBadges, ScoreRing, SkillChips, TopikBadge } from "../components/common.jsx";
import { useT } from "../i18n.jsx";

export default function JobDetailPage() {
  const { t } = useT();
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
  if (!job) return <p className="muted">{t("Loading…")}</p>;

  return (
    <div className="stack">
      <button className="link-btn muted small" onClick={() => navigate(-1)}>
        {t("← Back")}
      </button>
      <section className="card reveal">
        <div className="job-head">
          <div>
            <h1>{job.title}</h1>
            <div className="muted">{job.company}</div>
          </div>
          <JobBadges job={job} />
        </div>

        {match && (
          <div className="match-box">
            <ScoreRing score={match.score} size="lg" />
            <div className="match-detail">
              <div className="breakdown small">
                {t("Skill overlap {pct}% · Text similarity {sim}", {
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
                <SkillChips skills={match.missing_skills} kind="missing" empty={t("Nothing missing")} />
              </div>
            </div>
            <button className={`btn ${match.saved ? "btn-saved" : ""}`} onClick={toggleSave}>
              {t(match.saved ? "★ Saved" : "☆ Save")}
            </button>
          </div>
        )}
        {user && !match && (
          <p className="muted small">
            <Link to="/resume">{t("Upload your resume to see your match score for this posting.")}</Link>
          </p>
        )}

        <div className="skill-row">
          <span className="label">{t("Korean")}</span>
          <TopikBadge job={job} />
        </div>
        <div className="skill-row">
          <span className="label">{t("Required")}</span>
          <SkillChips skills={job.required_skills} />
        </div>
        <div className="skill-row">
          <span className="label">{t("Preferred")}</span>
          <SkillChips skills={job.preferred_skills} kind="preferred" />
        </div>

        <h3>{t("Description")}</h3>
        <p className="description">{job.description}</p>
        <p className="muted small">
          {t("Collected {date} · this is a snapshot, the original posting may have expired.", { date: job.collected_date ?? "—" })}{" "}
          {job.source_url && (
            <a href={job.source_url} target="_blank" rel="noreferrer">
              {t("Original posting ↗")}
            </a>
          )}
        </p>
      </section>
    </div>
  );
}
