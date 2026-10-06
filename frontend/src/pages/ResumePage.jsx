import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { ErrorBox } from "../components/common.jsx";

export default function ResumePage() {
  const [resume, setResume] = useState(null);
  const [skills, setSkills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const fileRef = useRef();

  const load = (r) => {
    setResume(r);
    setSkills(r?.skills ?? []);
    setSaved(false);
  };

  useEffect(() => {
    api
      .getResume()
      .then(load)
      .catch((e) => e.status !== 404 && setError(e))
      .finally(() => setLoading(false));
  }, []);

  async function upload(e) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      load(await api.uploadResume(file));
      fileRef.current.value = "";
    } catch (err) {
      setError(err);
    } finally {
      setUploading(false);
    }
  }

  async function saveSkills() {
    setSaving(true);
    setError(null);
    try {
      load(await api.updateSkills(skills));
      setSaved(true);
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  const dirty = resume && JSON.stringify([...skills].sort()) !== JSON.stringify([...resume.skills].sort());

  if (loading) return <p className="muted">Loading…</p>;

  return (
    <div className="stack">
      <Steps current={resume ? 2 : 1} />

      <section className="card">
        <h2>{resume ? "Replace your resume" : "Upload your resume"}</h2>
        <p className="muted">
          PDF only, up to 5 MB. Use a PDF exported from Word / Google Docs — scanned images can't be read.
        </p>
        <form onSubmit={upload} className="upload-row">
          <input ref={fileRef} type="file" accept="application/pdf,.pdf" required />
          <button className="btn btn-primary" disabled={uploading}>
            {uploading ? "Analyzing resume…" : "Upload & extract skills"}
          </button>
        </form>
      </section>

      <ErrorBox error={error} />

      {resume && (
        <section className="card">
          <div className="row-between">
            <h2>Extracted from your resume</h2>
            <span className="muted small">
              method: {resume.extraction_method === "llm" ? "AI (LLM)" : "keyword matching"}
            </span>
          </div>
          <dl className="facts">
            <dt>Education</dt>
            <dd>{resume.education || <span className="muted">not found</span>}</dd>
            <dt>Experience</dt>
            <dd>
              {resume.experience_years > 0 ? `${resume.experience_years} year(s)` : "No professional experience found"}
              {resume.experience && <div className="muted">{resume.experience}</div>}
            </dd>
          </dl>

          <h3>Skills ({skills.length})</h3>
          <p className="muted small">Check the list: remove anything wrong and add what was missed.</p>
          <SkillEditor skills={skills} onChange={setSkills} />

          <div className="row-between actions">
            <button className="btn btn-primary" onClick={saveSkills} disabled={!dirty || saving}>
              {saving ? "Saving…" : "Save skills"}
            </button>
            {saved && <span className="ok">Saved ✓</span>}
            <Link to="/recommendations" className="btn">
              See recommendations →
            </Link>
          </div>
        </section>
      )}

      <DangerZone />
    </div>
  );
}

function Steps({ current }) {
  const steps = ["Sign up", "Upload resume", "View matches"];
  return (
    <ol className="steps">
      {steps.map((s, i) => (
        <li key={s} className={i < current ? "done" : i === current ? "active" : ""}>
          <span>{i + 1}</span> {s}
        </li>
      ))}
    </ol>
  );
}

function SkillEditor({ skills, onChange }) {
  const [input, setInput] = useState("");
  const [suggestions, setSuggestions] = useState([]);

  useEffect(() => {
    const t = setTimeout(() => {
      api.searchSkills(input).then(setSuggestions).catch(() => {});
    }, 150);
    return () => clearTimeout(t);
  }, [input]);

  const add = (value) => {
    const v = value.trim();
    if (v && !skills.some((s) => s.toLowerCase() === v.toLowerCase())) onChange([...skills, v]);
    setInput("");
  };

  return (
    <div>
      <div className="chips editable">
        {skills.map((s) => (
          <span key={s} className="chip">
            {s}
            <button onClick={() => onChange(skills.filter((x) => x !== s))} aria-label={`Remove ${s}`}>
              ×
            </button>
          </span>
        ))}
      </div>
      <form
        className="add-skill"
        onSubmit={(e) => {
          e.preventDefault();
          add(input);
        }}
      >
        <input
          list="skill-suggestions"
          placeholder="Add a skill, e.g. Docker"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <datalist id="skill-suggestions">
          {suggestions.map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
        <button className="btn">Add</button>
      </form>
    </div>
  );
}

function DangerZone() {
  const { signOut } = useAuth();
  const navigate = useNavigate();
  async function remove() {
    if (!window.confirm("Delete your account, resume and saved jobs permanently?")) return;
    await api.deleteAccount();
    signOut();
    navigate("/register");
  }
  return (
    <section className="card danger">
      <h3>Your data</h3>
      <p className="muted small">Your resume is visible only to you. You can delete everything at any time.</p>
      <button className="btn btn-danger" onClick={remove}>
        Delete my account and data
      </button>
    </section>
  );
}
