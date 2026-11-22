import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { ErrorBox, Icon } from "../components/common.jsx";
import { useT } from "../i18n.jsx";

export default function AuthPage({ mode }) {
  const isRegister = mode === "register";
  const { t } = useT();
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
      {location.state?.deleted && (
        <div className="success reveal deleted-note" role="status">
          {t("Your account and all your data were deleted.")}
        </div>
      )}
      <section className="hero">
        <span className="eyebrow">{t("AI job search for Korea")}</span>
        <h1 className="hero-title">
          {t("Your resume in.")}
          <br />
          <span className="grad">{t("Live matches out.")}</span>
        </h1>
        <p className="hero-sub">
          {t(
            "Upload a PDF. We read your skills, search Wanted, Jumpit and JobKorea for fresh internships and entry-level roles, and rank them with a score you can understand."
          )}
        </p>
        <ol className="flowline">
          {["Read resume", "Search 3 job sites", "Score & skill gap"].map((s, i) => (
            <li key={s} style={{ "--i": i }}>
              <span>{i + 1}</span>
              {t(s)}
            </li>
          ))}
        </ol>
        <div className="sites">
          {["Wanted", "Jumpit", "JobKorea"].map((s) => (
            <span key={s}>{t(s)}</span>
          ))}
        </div>
      </section>

      <div className="card auth-card">
        <h2>{t(isRegister ? "Create your account" : "Welcome back")}</h2>
        <p className="muted small">
          {t(isRegister ? "Free. Your resume is visible only to you." : "Log in to see your matches.")}
        </p>
        <form onSubmit={submit} className="form">
          {isRegister && (
            <label>
              {t("Name")}
              <input value={form.name} onChange={set("name")} required maxLength={100} />
            </label>
          )}
          <label>
            {t("Email")}
            <input type="email" value={form.email} onChange={set("email")} required autoComplete="email" />
          </label>
          <label>
            {t("Password")}
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
            {busy ? <span className="spinner" /> : t(isRegister ? "Create account" : "Log in")}
            {!busy && <Icon name="arrow" />}
          </button>
        </form>
        <p className="muted small">
          {isRegister ? (
            <>{t("Already have an account?")} <Link to="/login">{t("Log in")}</Link></>
          ) : (
            <>{t("New here?")} <Link to="/register">{t("Create an account")}</Link></>
          )}
        </p>
      </div>
    </div>
  );
}
