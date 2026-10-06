const TOKEN_KEY = "jobassist.token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY));

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function request(method, path, { body, form, params } = {}) {
  const url = new URL(path, window.location.origin);
  Object.entries(params || {}).forEach(([k, v]) => v !== "" && v != null && url.searchParams.set(k, v));

  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(url, {
    method,
    headers,
    body: form ?? (body !== undefined ? JSON.stringify(body) : undefined),
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    let msg = data?.detail ?? res.statusText;
    if (Array.isArray(msg)) msg = msg.map((d) => d.msg).join("; ");
    if (res.status === 401 && token) setToken(null);
    throw new ApiError(res.status, msg);
  }
  return data;
}

export const api = {
  register: (name, email, password) => request("POST", "/api/auth/register", { body: { name, email, password } }),
  login: (email, password) => request("POST", "/api/auth/login", { body: { email, password } }),
  me: () => request("GET", "/api/auth/me"),
  deleteAccount: () => request("DELETE", "/api/users/me"),

  getResume: () => request("GET", "/api/resume"),
  uploadResume: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("POST", "/api/resume", { form });
  },
  updateSkills: (skills) => request("PUT", "/api/resume/skills", { body: { skills } }),
  searchSkills: (q) => request("GET", "/api/skills", { params: { q, limit: 15 } }),

  jobs: (params) => request("GET", "/api/jobs", { params }),
  jobMeta: () => request("GET", "/api/jobs/meta"),
  job: (id) => request("GET", `/api/jobs/${id}`),

  recommendations: (params) => request("GET", "/api/matches", { params }),
  matchForJob: (id) => request("GET", `/api/matches/${id}`),

  saved: () => request("GET", "/api/saved"),
  save: (id) => request("POST", `/api/saved/${id}`),
  unsave: (id) => request("DELETE", `/api/saved/${id}`),
};
