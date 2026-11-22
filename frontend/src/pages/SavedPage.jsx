import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { ErrorBox, JobCard, SkillChips } from "../components/common.jsx";
import { useT } from "../i18n.jsx";

export default function SavedPage() {
  const { t } = useT();
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.saved().then(setItems).catch(setError);
  }, []);

  async function remove(id) {
    await api.unsave(id);
    setItems(items.filter((i) => i.job.job_id !== id));
  }

  return (
    <div className="stack">
      <h1>{t("Saved postings")}</h1>
      <ErrorBox error={error} />
      {items?.length === 0 && (
        <div className="card empty">
          {t("Nothing saved yet.")} <Link to="/recommendations">{t("Browse your matches and press ☆ Save.")}</Link>
        </div>
      )}
      {items?.map(({ job, saved_at }, i) => (
        <JobCard key={job.job_id} job={job} index={i}>
          <div className="row-between">
            <SkillChips skills={job.required_skills} />
            <div className="row">
              <span className="muted small">{t("saved {date}", { date: new Date(saved_at).toLocaleDateString() })}</span>
              <button className="btn btn-ghost" onClick={() => remove(job.job_id)}>
                {t("Remove")}
              </button>
            </div>
          </div>
        </JobCard>
      ))}
    </div>
  );
}
