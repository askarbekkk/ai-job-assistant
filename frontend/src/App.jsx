import { NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { AuthProvider, RequireAuth, useAuth } from "./auth.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import ResumePage from "./pages/ResumePage.jsx";
import JobsPage from "./pages/JobsPage.jsx";
import JobDetailPage from "./pages/JobDetailPage.jsx";
import RecommendationsPage from "./pages/RecommendationsPage.jsx";
import SavedPage from "./pages/SavedPage.jsx";

function Header() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  return (
    <header className="header">
      <NavLink to="/" className="brand">
        JobMatch<span>.kr</span>
      </NavLink>
      <nav>
        {user && <NavLink to="/resume">1 · Resume</NavLink>}
        {user && <NavLink to="/recommendations">2 · Recommendations</NavLink>}
        <NavLink to="/jobs">All jobs</NavLink>
        {user && <NavLink to="/saved">Saved</NavLink>}
      </nav>
      <div className="header-user">
        {user ? (
          <>
            <span className="muted">{user.name}</span>
            <button
              className="btn btn-ghost"
              onClick={() => {
                signOut();
                navigate("/login");
              }}
            >
              Log out
            </button>
          </>
        ) : (
          <NavLink to="/login" className="btn btn-primary">
            Log in
          </NavLink>
        )}
      </div>
    </header>
  );
}

function Home() {
  const { user, loading } = useAuth();
  if (loading) return null;
  return <Navigate to={user ? "/recommendations" : "/login"} replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <Header />
      <main className="container">
        <Routes>
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
      </main>
    </AuthProvider>
  );
}
