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

const LIVE_SITE = /(wanted|jobkorea|jumpit)\./i;
const SITE_LABEL = { wanted: "Wanted", jobkorea: "JobKorea", jumpit: "Jumpit" };

export function JobCard({ job, index = 0, children }) {
  const site = job.source_url?.match(LIVE_SITE)?.[1]?.toLowerCase();
  return (
    <article className="card job-card reveal" style={{ "--i": index }}>
      <div className="job-head">
        <div className="job-name">
          <Link to={`/jobs/${job.job_id}`} className="job-title">
            {job.title}
          </Link>
          <div className="company">
            <span className="company-logo" aria-hidden="true">
              {job.company.replace(/^via /, "")[0]}
            </span>
            {job.company}
            {site && (
              <span className="live-pill" title="Found by live search after your upload">
                <i /> {SITE_LABEL[site]}
              </span>
            )}
          </div>
        </div>
        <JobBadges job={job} />
      </div>
      {children}
    </article>
  );
}

/** Animates a number from 0 to `value` once (skipped when the user prefers less motion). */
export function useCountUp(value, ms = 900) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      setShown(value);
      return;
    }
    let raf;
    const start = performance.now();
    const tick = (now) => {
      const t = Math.min(1, (now - start) / ms);
      setShown(value * (1 - Math.pow(1 - t, 3)));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, ms]);
  return shown;
}

export function ScoreRing({ score, size = "md" }) {
  const tone = score >= 70 ? "good" : score >= 45 ? "mid" : "low";
  const shown = useCountUp(score);
  return (
    <div className={`score-ring ${tone} ${size}`} style={{ "--p": score }} role="img" aria-label={`Match score ${Math.round(score)} of 100`}>
      <span>{Math.round(shown)}</span>
    </div>
  );
}

const ICONS = {
  check: "M5 12.5l4.5 4.5L19 7.5",
  file: "M7 3h7l5 5v13H7zM14 3v5h5M10 13h6M10 17h6",
  spark: "M12 3l2.2 5.8L20 11l-5.8 2.2L12 19l-2.2-5.8L4 11l5.8-2.2z",
  briefcase: "M4 8h16v11H4zM9 8V5h6v3M4 13h16",
  star: "M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z",
  logout: "M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10",
  upload: "M12 16V4M7 9l5-5 5 5M4 16v4h16v-4",
  arrow: "M5 12h14M13 6l6 6-6 6",
  search: "M11 4a7 7 0 100 14 7 7 0 000-14zM20 20l-4-4",
};

export function Icon({ name }) {
  return (
    <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={ICONS[name]} />
    </svg>
  );
}

export function ErrorBox({ error }) {
  if (!error) return null;
  return (
    <div className="error" role="alert">
      {String(error.message || error)}
    </div>
  );
}

export function SkeletonCards({ count = 3 }) {
  return Array.from({ length: count }, (_, i) => <div key={i} className="card skeleton" aria-hidden="true" />);
}
