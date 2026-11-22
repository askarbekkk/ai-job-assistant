import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { ErrorBox, Icon } from "../components/common.jsx";

export default function AuthPage({ mode }) {
  const isRegister = mode === "register";
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = isRegister
        ? await api.register(form.name, form.email, form.password)
        : await api.login(form.email, form.password);
      signIn(res);
      navigate(isRegister ? "/resume" : location.state?.from || "/recommendations", { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <section className="hero">
        <span className="eyebrow">AI job search for Korea</span>
        <h1 className="hero-title">
          Your resume in.
          <br />
          <span className="grad">Live matches out.</span>
        </h1>
        <p className="hero-sub">
          Upload a PDF. We read your skills, search Wanted, Jumpit and JobKorea for fresh internships and entry-level
          roles, and rank them with a score you can understand.
        </p>
        <ol className="flowline">
          {["Read resume", "Search 3 job sites", "Score & skill gap"].map((s, i) => (
            <li key={s} style={{ "--i": i }}>
              <span>{i + 1}</span>
              {s}
            </li>
          ))}
        </ol>
        <div className="sites">
          {["Wanted", "Jumpit", "JobKorea"].map((s) => (
            <span key={s}>{s}</span>
          ))}
        </div>
      </section>

      <div className="card auth-card">
        <h2>{isRegister ? "Create your account" : "Welcome back"}</h2>
        <p className="muted small">
          {isRegister ? "Free. Your resume is visible only to you." : "Log in to see your matches."}
        </p>
        <form onSubmit={submit} className="form">
          {isRegister && (
            <label>
              Name
              <input value={form.name} onChange={set("name")} required maxLength={100} />
            </label>
          )}
          <label>
            Email
            <input type="email" value={form.email} onChange={set("email")} required autoComplete="email" />
          </label>
          <label>
            Password
            <input
              type="password"
              value={form.password}
              onChange={set("password")}
              required
              minLength={isRegister ? 8 : undefined}
              autoComplete={isRegister ? "new-password" : "current-password"}
            />
          </label>
          <ErrorBox error={error} />
          <button className="btn btn-primary btn-lg" disabled={busy}>
            {busy ? <span className="spinner" /> : isRegister ? "Create account" : "Log in"}
            {!busy && <Icon name="arrow" />}
          </button>
        </form>
        <p className="muted small">
          {isRegister ? (
            <>Already have an account? <Link to="/login">Log in</Link></>
          ) : (
            <>New here? <Link to="/register">Create an account</Link></>
          )}
        </p>
      </div>
    </div>
  );
}
