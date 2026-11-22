import { createContext, useContext, useEffect, useState } from "react";
import api, { refreshSession, setAuthFailHandler, setToken } from "./api";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setAuthFailHandler(() => { setToken(null); setUser(null); });
    // On first load, the httpOnly refresh cookie (if any) brings the session back.
    refreshSession().then((d) => setUser(d.user)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const start = (data) => { setToken(data.access_token); setUser(data.user); };
  const login = async (email, password, remember_me) =>
    start((await api.post("/auth/login", { email, password, remember_me })).data);
  const register = async (name, email, password, remember_me) =>
    start((await api.post("/auth/register", { name, email, password, remember_me })).data);
  const logout = async () => {
    try { await api.post("/auth/logout"); } finally { setToken(null); setUser(null); }
  };

  return <Ctx.Provider value={{ user, loading, login, register, logout }}>{children}</Ctx.Provider>;
}
