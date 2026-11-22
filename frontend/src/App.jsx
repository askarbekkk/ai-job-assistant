import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { onLoadingChange } from "./api.js";
import { AuthProvider, RequireAuth, useAuth } from "./auth.jsx";
import { Icon } from "./components/common.jsx";
import { LangProvider, useT } from "./i18n.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import ResumePage from "./pages/ResumePage.jsx";
import JobsPage from "./pages/JobsPage.jsx";
import JobDetailPage from "./pages/JobDetailPage.jsx";
import RecommendationsPage from "./pages/RecommendationsPage.jsx";
import SavedPage from "./pages/SavedPage.jsx";

function navItems(user) {
  return [
    user && { to: "/resume", label: "Resume", icon: "file" },
    user && { to: "/recommendations", label: "Matches", icon: "spark" },
    { to: "/jobs", label: "All jobs", icon: "briefcase" },
    user && { to: "/saved", label: "Saved", icon: "star" },
  ].filter(Boolean);
}

function Brand() {
  return (
    <NavLink to="/" className="brand" aria-label="JobMatch home">
      <span className="brand-mark">
        <Icon name="check" />
      </span>
      <span>
        JobMatch<span className="brand-tld">.kr</span>
      </span>
    </NavLink>
  );
}

const THEME_KEY = "jobassist.theme";

/** Light / dark switch. Until the user picks, the page follows the phone's setting. */
function useTheme() {
  const systemDark = () => window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem(THEME_KEY) || (systemDark() ? "dark" : "light");
    } catch {
      return systemDark() ? "dark" : "light";
    }
  });
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.querySelectorAll('meta[name="theme-color"]').forEach((m) => (m.content = theme === "dark" ? "#0b1118" : "#f4f6f8"));
  }, [theme]);
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch {
      /* storage unavailable */
    }
  };
  return [theme, toggle];
}

function Header() {
  const { user, signOut } = useAuth();
  const { t, lang, setLang } = useT();
  const [theme, toggleTheme] = useTheme();
  const navigate = useNavigate();
  return (
    <header className="header">
      <div className="header-inner">
        <Brand />
        <nav className="topnav">
          {navItems(user).map((n) => (
            <NavLink key={n.to} to={n.to}>
              {t(n.label)}
            </NavLink>
          ))}
        </nav>
        <div className="header-user">
          <div className="lang-switch" role="group" aria-label="Language">
            {[
              ["en", "EN"],
              ["ko", "한"],
            ].map(([code, label]) => (
              <button key={code} className={lang === code ? "on" : ""} aria-pressed={lang === code} onClick={() => setLang(code)}>
                {label}
              </button>
            ))}
          </div>
          <button
            className="btn btn-ghost btn-icon theme-btn"
            onClick={toggleTheme}
            aria-label={t(theme === "dark" ? "Light mode" : "Dark mode")}
            title={t(theme === "dark" ? "Light mode" : "Dark mode")}
          >
            <Icon name={theme === "dark" ? "sun" : "moon"} />
          </button>
          {user ? (
            <>
              <span className="avatar" title={user.name}>
                {user.name?.[0]?.toUpperCase() ?? "?"}
              </span>
              <button
                className="btn btn-ghost btn-icon"
                aria-label={t("Log out")}
                title={t("Log out")}
                onClick={() => {
                  signOut();
                  navigate("/login");
                }}
              >
                <Icon name="logout" />
              </button>
            </>
          ) : (
            <NavLink to="/login" className="btn btn-primary">
              {t("Log in")}
            </NavLink>
          )}
        </div>
      </div>
    </header>
  );
}

/** Phone navigation: a tab bar at the bottom, within thumb reach. */
function TabBar() {
  const { user } = useAuth();
  const { t } = useT();
  return (
    <nav className="tabbar" aria-label="Main">
      {navItems(user).map((n) => (
        <NavLink key={n.to} to={n.to}>
          <Icon name={n.icon} />
          <span>{t(n.label)}</span>
        </NavLink>
      ))}
    </nav>
  );
}

/** Thin bar at the top: runs on every page change and while the server is answering. */
function TopProgress() {
  const { pathname } = useLocation();
  const [busy, setBusy] = useState(false);
  const [kick, setKick] = useState(false);
  const [progress, setProgress] = useState(0);
  const [visible, setVisible] = useState(false);

  useEffect(() => onLoadingChange(setBusy), []);
  useEffect(() => {
    // A new page starts at the top. "instant": a smooth scroll is cut off when the page content swaps.
    window.scrollTo({ top: 0, behavior: "instant" });
    setKick(true);
    const t = setTimeout(() => setKick(false), 350);
    return () => clearTimeout(t);
  }, [pathname]);

  const active = busy || kick;
  useEffect(() => {
    if (active) {
      setVisible(true);
      setProgress((p) => Math.max(p, 0.12));
      // Creep toward 90% and wait there: the real end comes when the request finishes.
      const t = setInterval(() => setProgress((p) => p + (0.9 - p) * 0.09), 180);
      return () => clearInterval(t);
    }
    setProgress(1);
    const t = setTimeout(() => {
      setVisible(false);
      setProgress(0);
    }, 420);
    return () => clearTimeout(t);
  }, [active]);

  return (
    <div
      className={`topbar ${visible ? "on" : ""}`}
      style={{ transform: `scaleX(${progress})` }}
      role="progressbar"
      aria-label="Loading"
      aria-hidden={!visible}
    />
  );
}

function Home() {
  const { user, loading } = useAuth();
  if (loading) return null;
  return <Navigate to={user ? "/recommendations" : "/login"} replace />;
}

function NotFound() {
  const { t } = useT();
  return <p>{t("Page not found.")}</p>;
}

export default function App() {
  return (
    <LangProvider>
      <Shell />
    </LangProvider>
  );
}

function Shell() {
  const location = useLocation();
  return (
    <AuthProvider>
      <div className="aurora" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <TopProgress />
      <Header />
      <main className="container">
        {/* keyed by path so every page change plays the enter animation */}
        <div className="page" key={location.pathname}>
          <Routes location={location}>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<AuthPage mode="login" />} />
            <Route path="/register" element={<AuthPage mode="register" />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/jobs/:jobId" element={<JobDetailPage />} />
            <Route path="/resume" element={<RequireAuth><ResumePage /></RequireAuth>} />
            <Route path="/recommendations" element={<RequireAuth><RecommendationsPage /></RequireAuth>} />
            <Route path="/saved" element={<RequireAuth><SavedPage /></RequireAuth>} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </div>
      </main>
      <TabBar />
    </AuthProvider>
  );
}
