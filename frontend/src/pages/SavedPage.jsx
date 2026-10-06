import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { ErrorBox, JobCard, SkillChips } from "../components/common.jsx";

export default function SavedPage() {
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
      <h1>Saved postings</h1>
      <ErrorBox error={error} />
      {items?.length === 0 && (
        <div className="card empty">
          Nothing saved yet. <Link to="/recommendations">Browse your matches</Link> and press ☆ Save.
        </div>
      )}
      {items?.map(({ job, saved_at }) => (
        <JobCard key={job.job_id} job={job}>
          <div className="row-between">
            <SkillChips skills={job.required_skills} />
            <div className="row">
              <span className="muted small">saved {new Date(saved_at).toLocaleDateString()}</span>
              <button className="btn btn-ghost" onClick={() => remove(job.job_id)}>
                Remove
              </button>
            </div>
          </div>
        </JobCard>
      ))}
    </div>
  );
}
