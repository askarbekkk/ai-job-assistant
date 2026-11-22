import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { ErrorBox, Icon } from "../components/common.jsx";

export default function ResumePage() {
  const [resume, setResume] = useState(null);
  const [skills, setSkills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [fileName, setFileName] = useState("");
  const [dragging, setDragging] = useState(false);
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
      setFileName(""); // the form is unmounted during the upload, so the input is already empty
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
        <p className="muted small">
          PDF only, up to 5 MB. Use a PDF exported from Word / Google Docs — scanned images can't be read.
        </p>
        {uploading ? (
          <UploadProgress />
        ) : (
          <form onSubmit={upload} className="upload-form">
            <label
              className={`dropzone ${dragging ? "dragging" : ""} ${fileName ? "has-file" : ""}`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                if (e.dataTransfer.files[0]) {
                  fileRef.current.files = e.dataTransfer.files;
                  setFileName(e.dataTransfer.files[0].name);
                }
              }}
            >
              <span className="dz-icon">
                <Icon name="upload" />
              </span>
              <strong>{fileName || "Drop your PDF here"}</strong>
              <span className="muted small">{fileName ? "Ready to analyze" : "or tap to choose a file"}</span>
              <input
                ref={fileRef}
                type="file"
                accept="application/pdf,.pdf"
                required
                onChange={(e) => setFileName(e.target.files?.[0]?.name || "")}
              />
            </label>
            <button className="btn btn-primary btn-lg" disabled={!fileName}>
              Upload & find jobs <Icon name="arrow" />
            </button>
          </form>
        )}
        {resume?.live_jobs_found != null && !uploading && (
          <div className="success reveal">
            <span>
              <strong>{resume.live_jobs_found} postings found right now</strong> on Wanted, Jumpit and JobKorea for your
              skills.
            </span>
            <Link to="/recommendations" className="btn btn-primary">
              See your matches <Icon name="arrow" />
            </Link>
          </div>
        )}
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

const UPLOAD_STEPS = ["Reading your PDF", "Extracting skills", "Searching Wanted, Jumpit, JobKorea", "Scoring matches"];

/** The upload is one request; the steps advance on a timer to show what the server is doing. */
function UploadProgress() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setStep((s) => Math.min(s + 1, UPLOAD_STEPS.length - 1)), 1600);
    return () => clearInterval(t);
  }, []);
  return (
    <ol className="progress-steps" aria-live="polite">
      {UPLOAD_STEPS.map((s, i) => (
        <li key={s} className={i < step ? "done" : i === step ? "active" : ""}>
          <span className="ps-dot">{i < step ? <Icon name="check" /> : i === step ? <span className="spinner" /> : null}</span>
          {s}
        </li>
      ))}
    </ol>
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

/** idle → confirm → deleting → done (full-screen check), then back to the login page. */
function DangerZone() {
  const { signOut } = useAuth();
  const navigate = useNavigate();
  const [stage, setStage] = useState("idle");
  const [error, setError] = useState(null);

  async function remove() {
    setStage("deleting");
    setError(null);
    try {
      await api.deleteAccount();
      setStage("done");
      setTimeout(() => {
        navigate("/login", { replace: true, state: { deleted: true } });
        signOut();
      }, 1700);
    } catch (err) {
      setError(err);
      setStage("confirm");
    }
  }

  return (
    <section className={`card danger ${stage !== "idle" ? "armed" : ""}`}>
      <h3>Your data</h3>
      <p className="muted small">Your resume is visible only to you. You can delete everything at any time.</p>
      {stage === "idle" ? (
        <button className="btn btn-danger" onClick={() => setStage("confirm")}>
          Delete my account and data
        </button>
      ) : (
        <div className="confirm-box">
          <strong>Delete everything for good?</strong>
          <p className="muted small">Your account, resume, matches and saved jobs will be removed. This can't be undone.</p>
          <ErrorBox error={error} />
          <div className="row">
            <button className="btn btn-danger-solid" onClick={remove} disabled={stage !== "confirm"}>
              {stage === "deleting" ? <span className="spinner" /> : "Yes, delete"}
            </button>
            <button className="btn btn-ghost" onClick={() => setStage("idle")} disabled={stage !== "confirm"}>
              Cancel
            </button>
          </div>
        </div>
      )}
      {stage === "done" &&
        // Portal: the animated page wrapper would otherwise clip a fixed overlay to itself.
        createPortal(
        <div className="farewell" role="status">
          <div className="farewell-card">
            <svg className="check-draw" viewBox="0 0 52 52" aria-hidden="true">
              <circle cx="26" cy="26" r="24" />
              <path d="M15 27l7 7 15-16" />
            </svg>
            <strong>Account deleted</strong>
            <span className="muted small">Your resume and data are gone. Taking you to the login page…</span>
          </div>
        </div>,
        document.body
      )}
    </section>
  );
}
