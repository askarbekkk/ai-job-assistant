import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { ErrorBox } from "../components/common.jsx";

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
      <div className="card auth-card">
        <h1>{isRegister ? "Create an account" : "Log in"}</h1>
        <p className="muted">
          Find internships and entry-level jobs in Korea that match your resume — and see which skills to learn next.
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
          <button className="btn btn-primary" disabled={busy}>
            {busy ? "…" : isRegister ? "Sign up" : "Log in"}
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
