import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import api, { errMsg } from "../api";
import Icon from "../components/Icon";

const AGENTS = {
  stock_finder_agent: { label: "Stock finder", icon: "search", c: "indigo" },
  market_data_agent: { label: "Market data", icon: "chart", c: "teal" },
  news_analyst_agent: { label: "News analyst", icon: "news", c: "amber" },
  price_recommender_agent: { label: "Price recommender", icon: "target", c: "pink" },
};
const STATUS = { running: "Running", done: "Done", error: "Failed" };
const md = { table: (p) => <div className="scroll"><table {...p} /></div> };

export default function Agent() {
  const [runs, setRuns] = useState([]);
  const [open, setOpen] = useState(null);
  const [query, setQuery] = useState("Give me good stock recommendation from NSE");
  const [err, setErr] = useState("");

  const loadRuns = useCallback(async () => {
    try { setRuns((await api.get("/agent/runs")).data); } catch (e) { setErr(errMsg(e)); }
  }, []);
  const select = useCallback(async (id) => {
    try { setOpen((await api.get(`/agent/runs/${id}`)).data); } catch (e) { setErr(errMsg(e)); }
  }, []);

  useEffect(() => { loadRuns(); }, [loadRuns]);

  const running = runs.some((r) => r.status === "running");
  useEffect(() => {
    if (!running) return;
    const t = setInterval(async () => { await loadRuns(); if (open) select(open.id); }, 4000);
    return () => clearInterval(t);
  }, [running, open, loadRuns, select]);

  const start = async () => {
    setErr("");
    try {
      const { data } = await api.post("/agent/runs", { query });
      await loadRuns(); select(data.id);
    } catch (e) { setErr(errMsg(e)); }
  };

  return (
    <div className="agent">
      <section className="panel side">
        <div className="agent-head">
          <span className="logo-mark"><Icon name="spark" size={18} /></span>
          <div><h1>AI stock picks</h1><p>Four agents research, check data and news, then suggest an action.</p></div>
        </div>
        <label>What should they look for?
          <input value={query} onChange={(e) => setQuery(e.target.value)} maxLength={500} />
        </label>
        <button className="btn primary" onClick={start} disabled={running}>{running ? "Agents are working…" : "Run analysis"}</button>
        {err && <div className="error">{err}</div>}
        <p className="fine">AI-generated ideas, not investment advice. Check them yourself before trading.</p>
        <h2>Past runs</h2>
        {runs.length === 0 && <p className="muted">No runs yet.</p>}
        <ul className="runs">
          {runs.map((r) => (
            <li key={r.id}>
              <button className={open?.id === r.id ? "on" : ""} onClick={() => select(r.id)}>
                <span>{new Date(r.created_at).toLocaleString()}</span>
                <span className={`tag ${r.status}`}>{r.status === "running" && <i className="dot" />}{STATUS[r.status]}</span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel result">
        {!open ? (
          <div className="empty"><span className="empty-ico"><Icon name="spark" size={28} /></span>
            <p className="muted">Pick a run, or start a new one, to see the recommendation.</p></div>
        ) : (
          <>
            <h2>{open.query}</h2>
            {open.status === "running" && (
              <div className="working"><i className="bars"><b /><b /><b /></i>The agents are working. This page updates by itself.</div>
            )}
            {open.status === "error" && <div className="error">The run failed: {open.error}</div>}
            {open.final && <div className="md final"><ReactMarkdown remarkPlugins={[remarkGfm]} components={md}>{open.final}</ReactMarkdown></div>}
            {open.steps?.length > 0 && (
              <>
                <h3 className="steps-title">What each agent found</h3>
                <div className="steps">
                  {open.steps.map((s, i) => {
                    const a = AGENTS[s.agent] || { label: s.agent, icon: "spark", c: "indigo" };
                    return (
                      <details key={i} className={`step ${a.c}`}>
                        <summary><span className="ico"><Icon name={a.icon} size={16} /></span>{a.label}</summary>
                        <div className="md"><ReactMarkdown remarkPlugins={[remarkGfm]} components={md}>{s.content}</ReactMarkdown></div>
                      </details>
                    );
                  })}
                </div>
              </>
            )}
          </>
        )}
      </section>
    </div>
  );
}
