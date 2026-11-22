import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { onLoadingChange } from "./api.js";
import { AuthProvider, RequireAuth, useAuth } from "./auth.jsx";
import { Icon } from "./components/common.jsx";
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

function Header() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  return (
    <header className="header">
      <div className="header-inner">
        <Brand />
        <nav className="topnav">
          {navItems(user).map((n) => (
            <NavLink key={n.to} to={n.to}>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="header-user">
          {user ? (
            <>
              <span className="avatar" title={user.name}>
                {user.name?.[0]?.toUpperCase() ?? "?"}
              </span>
              <button
                className="btn btn-ghost btn-icon"
                aria-label="Log out"
                title="Log out"
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
              Log in
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
  return (
    <nav className="tabbar" aria-label="Main">
      {navItems(user).map((n) => (
        <NavLink key={n.to} to={n.to}>
          <Icon name={n.icon} />
          <span>{n.label}</span>
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

export default function App() {
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
            <Route path="*" element={<p>Page not found.</p>} />
          </Routes>
        </div>
      </main>
      <TabBar />
    </AuthProvider>
  );
}
