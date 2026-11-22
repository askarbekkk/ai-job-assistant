import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useT } from "../i18n.jsx";

const FILTERS_KEY = "jobassist.filters";
const EMPTY_FILTERS = { employment_type: "", location: "", topik: "" };

/** Filters shared by the job list and recommendations; remembered per browser. */
export function useFilters() {
  const [filters, setFilters] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(FILTERS_KEY) || "{}");
      // only known keys: an older version stored "korean_level"
      return Object.fromEntries(Object.keys(EMPTY_FILTERS).map((k) => [k, saved[k] ?? ""]));
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
  const { t } = useT();
  const [meta, setMeta] = useState({ locations: [], employment_types: [] });
  useEffect(() => {
    api.jobMeta().then(setMeta).catch(() => {});
  }, []);
  const set = (key) => (e) => onChange({ ...filters, [key]: e.target.value });

  return (
    <div className="filters">
      {children}
      <label>
        {t("Job type")}
        <select value={filters.employment_type} onChange={set("employment_type")}>
          <option value="">{t("Any")}</option>
          {meta.employment_types.map((v) => (
            <option key={v} value={v}>
              {t(v)}
            </option>
          ))}
        </select>
      </label>
      <label>
        {t("Location")}
        <select value={filters.location} onChange={set("location")}>
          <option value="">{t("Anywhere")}</option>
          {meta.locations.map((v) => (
            <option key={v} value={v}>
              {t(v)}
            </option>
          ))}
        </select>
      </label>
      <label title={t("Postings that need a higher Korean level than yours are hidden")}>
        {t("My Korean (TOPIK)")}
        <select value={filters.topik} onChange={set("topik")}>
          <option value="">{t("Show all")}</option>
          <option value="0">{t("Korean not needed only")}</option>
          {[1, 2, 3, 4, 5, 6].map((n) => (
            <option key={n} value={n}>
              {t("TOPIK {n}", { n })}
            </option>
          ))}
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

/** How much Korean the posting needs: "Korean not required" or "TOPIK 4+", marked "est." when guessed. */
export function TopikBadge({ job }) {
  const { t } = useT();
  if (job.topik_level === 0) return <span className="badge badge-green">{t("Korean not required")}</span>;
  return (
    <span
      className={`badge ${job.topik_stated ? "badge-amber" : ""}`}
      title={t(job.topik_stated ? "The posting states this TOPIK level" : "Estimated: the posting does not state a TOPIK level")}
    >
      {t("TOPIK {n}+", { n: job.topik_level })}
      {!job.topik_stated && <em className="est"> · {t("est.")}</em>}
    </span>
  );
}

export function JobBadges({ job }) {
  const { t } = useT();
  return (
    <div className="badges">
      <span className={`badge ${job.employment_type === "Internship" ? "badge-blue" : "badge-purple"}`}>
        {t(job.employment_type)}
      </span>
      <span className="badge">{t(job.location)}</span>
      <TopikBadge job={job} />
    </div>
  );
}

const LIVE_SITE = /(wanted|jobkorea|jumpit)\./i;
const SITE_LABEL = { wanted: "Wanted", jobkorea: "JobKorea", jumpit: "Jumpit" };

export function JobCard({ job, index = 0, children }) {
  const { t } = useT();
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
                <i /> {t(SITE_LABEL[site])}
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
  moon: "M20 14.5A8 8 0 019.5 4a8 8 0 1010.5 10.5z",
  sun: "M12 8a4 4 0 100 8 4 4 0 000-8zM12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4",
  plus: "M12 5v14M5 12h14",
  chevron: "M9 6l6 6-6 6",
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
