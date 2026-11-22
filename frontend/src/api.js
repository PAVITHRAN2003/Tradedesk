import axios from "axios";

let accessToken = null;           // kept in memory only; the refresh cookie restores it
let onAuthFail = () => {};
export const setToken = (t) => (accessToken = t);
export const setAuthFailHandler = (fn) => (onAuthFail = fn);

const api = axios.create({ baseURL: "/api", withCredentials: true });

api.interceptors.request.use((cfg) => {
  if (accessToken) cfg.headers.Authorization = `Bearer ${accessToken}`;
  return cfg;
});

// One shared in-flight refresh: refresh tokens rotate, so parallel calls must not race.
let inflight = null;
export function refreshSession() {
  inflight ||= axios
    .post("/api/auth/refresh", null, { withCredentials: true })
    .then((r) => { setToken(r.data.access_token); return r.data; })
    .finally(() => { inflight = null; });
  return inflight;
}

api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const req = err.config;
    if (err.response?.status === 401 && req && !req._retry && !req.url.startsWith("/auth/")) {
      req._retry = true;
      try {
        await refreshSession();
        return api(req);
      } catch {
        onAuthFail();
      }
    }
    return Promise.reject(err);
  }
);

export const errMsg = (e) => {
  const d = e.response?.data?.detail;
  if (Array.isArray(d)) return d.map((x) => x.msg).join(", ");
  return d || e.message || "Something went wrong";
};

export default api;
