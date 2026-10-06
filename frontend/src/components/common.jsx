import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";

const FILTERS_KEY = "jobassist.filters";
const EMPTY_FILTERS = { employment_type: "", location: "", korean_level: "" };

/** Filters shared by the job list and recommendations; remembered per browser. */
export function useFilters() {
  const [filters, setFilters] = useState(() => {
    try {
      return { ...EMPTY_FILTERS, ...JSON.parse(localStorage.getItem(FILTERS_KEY) || "{}") };
    } catch {
      return EMPTY_FILTERS;
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem(FILTERS_KEY, JSON.stringify(filters));
    } catch {
      /* storage unavailable */
    }
  }, [filters]);
  return [filters, setFilters];
}

export function FilterBar({ filters, onChange, children }) {
  const [meta, setMeta] = useState({ locations: [], employment_types: [], korean_levels: [] });
  useEffect(() => {
    api.jobMeta().then(setMeta).catch(() => {});
  }, []);
  const set = (key) => (e) => onChange({ ...filters, [key]: e.target.value });

  return (
    <div className="filters">
      {children}
      <label>
        Job type
        <select value={filters.employment_type} onChange={set("employment_type")}>
          <option value="">Any</option>
          {meta.employment_types.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
      </label>
      <label>
        Location
        <select value={filters.location} onChange={set("location")}>
          <option value="">Anywhere</option>
          {meta.locations.map((l) => (
            <option key={l}>{l}</option>
          ))}
        </select>
      </label>
      <label title="Postings that need a higher Korean level than yours are hidden">
        My Korean level
        <select value={filters.korean_level} onChange={set("korean_level")}>
          <option value="">Show all</option>
          <option value="None">None — Korean not required only</option>
          <option value="Basic">Basic</option>
          <option value="Fluent">Fluent</option>
        </select>
      </label>
    </div>
  );
}

export function SkillChips({ skills, kind = "", empty = "—" }) {
  if (!skills?.length) return <span className="muted">{empty}</span>;
  return (
    <div className="chips">
      {skills.map((s) => (
        <span key={s} className={`chip ${kind}`}>
          {s}
        </span>
      ))}
    </div>
  );
}

const KOREAN_LABEL = { None: "Korean not required", Basic: "Basic Korean", Fluent: "Fluent Korean" };

export function JobBadges({ job }) {
  return (
    <div className="badges">
      <span className={`badge ${job.employment_type === "Internship" ? "badge-blue" : "badge-purple"}`}>
        {job.employment_type}
      </span>
      <span className="badge">{job.location}</span>
      <span className={`badge ${job.korean_required === "None" ? "badge-green" : ""}`}>
        {KOREAN_LABEL[job.korean_required] ?? job.korean_required}
      </span>
    </div>
  );
}

export function JobCard({ job, children }) {
  return (
    <article className="card job-card">
      <div className="job-head">
        <div>
          <Link to={`/jobs/${job.job_id}`} className="job-title">
            {job.title}
          </Link>
          <div className="muted">{job.company}</div>
        </div>
        <JobBadges job={job} />
      </div>
      {children}
    </article>
  );
}

export function ScoreRing({ score }) {
  const tone = score >= 70 ? "good" : score >= 45 ? "mid" : "low";
  return (
    <div className={`score-ring ${tone}`} style={{ "--p": score }}>
      <span>{Math.round(score)}</span>
    </div>
  );
}

export function ErrorBox({ error }) {
  if (!error) return null;
  return <div className="error">{String(error.message || error)}</div>;
}
