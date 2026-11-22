import { useEffect, useState } from "react";
import { api } from "../api.js";
import { ErrorBox, FilterBar, JobCard, SkeletonCards, SkillChips, useFilters } from "../components/common.jsx";
import { useT } from "../i18n.jsx";

const PAGE_SIZE = 20;

export default function JobsPage() {
  const { t } = useT();
  const [filters, setFilters] = useFilters();
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const t = setTimeout(() => setQuery(q), 300);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => setPage(1), [filters, query]);

  useEffect(() => {
    api
      .jobs({ ...filters, q: query, page, page_size: PAGE_SIZE })
      .then(setData)
      .catch(setError);
  }, [filters, query, page]);

  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="stack">
      <div className="row-between">
        <h1>{t("All postings")}</h1>
        {data && <span className="muted small">{t("{n} found", { n: data.total })}</span>}
      </div>
      <FilterBar filters={filters} onChange={setFilters}>
        <label className="grow">
          {t("Search")}
          <input placeholder={t("Title, company or keyword")} value={q} onChange={(e) => setQ(e.target.value)} />
        </label>
      </FilterBar>
      <ErrorBox error={error} />
      {!data && !error && <SkeletonCards count={4} />}
      {data?.items.map((job, i) => (
        <JobCard key={job.job_id} job={job} index={i}>
          <div className="skill-row">
            <span className="label">{t("Required")}</span>
            <SkillChips skills={job.required_skills} />
          </div>
        </JobCard>
      ))}
      {pages > 1 && (
        <div className="pager">
          <button className="btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            {t("← Prev")}
          </button>
          <span className="muted">
            {page} / {pages}
          </span>
          <button className="btn" disabled={page >= pages} onClick={() => setPage(page + 1)}>
            {t("Next →")}
          </button>
        </div>
      )}
    </div>
  );
}
