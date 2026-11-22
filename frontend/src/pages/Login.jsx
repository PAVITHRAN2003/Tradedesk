import { useState } from "react";
import { errMsg } from "../api";
import { useAuth } from "../auth";
import Icon from "../components/Icon";

export default function Login() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ name: "", email: "", password: "", remember: true });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      if (mode === "login") await login(f.email, f.password, f.remember);
      else await register(f.name, f.email, f.password, f.remember);
    } catch (x) { setErr(errMsg(x)); } finally { setBusy(false); }
  };

  return (
    <div className="auth">
      <section className="auth-pitch">
        <span className="logo-mark lg"><Icon name="chart" size={24} /></span>
        <h1>Know what you actually made.</h1>
        <p>Your NSE trading journal, with research agents that look for the next idea.</p>
        <ul className="feats">
          <li><Icon name="list" />Log every buy and sell in seconds</li>
          <li><Icon name="value" />See real profit and loss for each stock</li>
          <li><Icon name="spark" />Get AI buy and sell ideas with target prices</li>
        </ul>
      </section>
      <div className="auth-form-wrap">
        <form className="auth-card" onSubmit={submit}>
          <h2>{mode === "login" ? "Welcome back" : "Create your account"}</h2>
          {mode === "register" && (
            <label>Name<input required value={f.name} onChange={set("name")} autoComplete="name" /></label>
          )}
          <label>Email<input required type="email" value={f.email} onChange={set("email")} autoComplete="email" /></label>
          <label>Password
            <input required type="password" minLength={mode === "register" ? 8 : 1} value={f.password} onChange={set("password")}
              autoComplete={mode === "login" ? "current-password" : "new-password"} />
          </label>
          {mode === "register" && <small className="hint">At least 8 characters.</small>}
          <label className="check"><input type="checkbox" checked={f.remember} onChange={set("remember")} /> Keep me signed in for 30 days</label>
          {err && <div className="error" role="alert">{err}</div>}
          <button className="btn primary" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}</button>
          <button type="button" className="link" onClick={() => { setMode(mode === "login" ? "register" : "login"); setErr(""); }}>
            {mode === "login" ? "New here? Create an account" : "Already have an account? Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
