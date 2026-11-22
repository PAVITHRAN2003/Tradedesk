import { useCallback, useEffect, useState } from "react";
import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api, { errMsg } from "../api";
import { useAuth } from "../auth";
import Icon from "../components/Icon";
import Ticker from "../components/Ticker";
import TradeModal from "../components/TradeModal";
import { inr, inrShort, pct, signed, tone } from "../format";

const COLORS = ["#6366f1", "#06b6d4", "#f59e0b", "#ec4899", "#10b981", "#8b5cf6", "#f97316", "#14b8a6"];
const tip = { background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 10, color: "var(--ink)", boxShadow: "var(--shadow)" };
const greeting = () => { const h = new Date().getHours(); return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening"; };

export default function Dashboard() {
  const { user } = useAuth();
  const [sum, setSum] = useState(null);
  const [trades, setTrades] = useState([]);
  const [modal, setModal] = useState(false);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    try {
      const [s, t] = await Promise.all([api.get("/portfolio/summary"), api.get("/trades")]);
      setSum(s.data); setTrades(t.data); setErr("");
    } catch (e) { setErr(errMsg(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const remove = async (id) => {
    if (!confirm("Delete this trade? Your holdings and profit figures will be recalculated.")) return;
    try { await api.delete(`/trades/${id}`); load(); } catch (e) { setErr(errMsg(e)); }
  };

  if (!sum) return <div className="splash">{err || "Loading your portfolio…"}</div>;
  const { totals: t, holdings, history } = sum;
  const pnlBars = history.map((h) => {
    const open = holdings.find((x) => x.symbol === h.symbol);
    return { symbol: h.symbol, pnl: +(h.realized + (open ? open.unrealized : 0)).toFixed(2) };
  });

  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">{greeting()}, {user.name.trim().split(" ")[0]}</p>
          <p className="hero-label">Total profit and loss</p>
          <div className="big">{signed(t.total_pnl)}</div>
          <div className="chips">
            <span className="chip">Booked <b>{signed(t.realized)}</b></span>
            <span className="chip">Unrealised <b>{signed(t.unrealized)}</b></span>
          </div>
        </div>
        <button className="btn light" onClick={() => setModal(true)}>+ Log a trade</button>
      </section>

      {err && <div className="error">{err}</div>}

      <section className="stats">
        <Stat c="indigo" icon="wallet" label="Invested now" value={inr(t.invested)} />
        <Stat c="teal" icon="value" label="Current value" value={inr(t.value)} />
        <Stat c="amber" icon="target" label="Win rate on sells" value={t.win_rate == null ? "No sells yet" : `${t.win_rate}%`} meter={t.win_rate} />
        <Stat c="pink" icon="list" label="Trades logged" value={t.trade_count} sub={`across ${t.symbols_traded} stocks`} />
      </section>

      {trades.length === 0 ? (
        <section className="panel empty">
          <span className="empty-ico"><Icon name="chart" size={30} /></span>
          <h2>No trades yet</h2>
          <p className="muted">Log your first buy and your holdings, allocation and profit will appear here.</p>
          <button className="btn primary" onClick={() => setModal(true)}>Log your first trade</button>
        </section>
      ) : (
        <>
          <section className="charts">
            <div className="panel">
              <h2>Where your money sits</h2>
              {holdings.length ? (
                <div className="donut">
                  <ResponsiveContainer width="100%" height={240}>
                    <PieChart>
                      <Pie data={holdings} dataKey="value" nameKey="symbol" innerRadius={68} outerRadius={100} paddingAngle={3} stroke="none">
                        {holdings.map((h, i) => <Cell key={h.symbol} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip formatter={(v) => inr(v)} contentStyle={tip} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="donut-mid"><span>Value</span><b>{inrShort(t.value)}</b></div>
                </div>
              ) : <p className="muted pad">You have no open positions.</p>}
              <ul className="legend">
                {holdings.map((h, i) => (
                  <li key={h.symbol}><i style={{ background: COLORS[i % COLORS.length] }} />{h.symbol}
                    <span>{t.value ? ((h.value / t.value) * 100).toFixed(1) : 0}%</span></li>
                ))}
              </ul>
            </div>
            <div className="panel">
              <h2>Profit and loss by stock</h2>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={pnlBars} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
                  <XAxis dataKey="symbol" tickLine={false} axisLine={false} fontSize={12} stroke="var(--muted)" />
                  <YAxis tickFormatter={(v) => (Math.abs(v) >= 1000 ? `${v / 1000}k` : v)} tickLine={false} axisLine={false} fontSize={12} width={48} stroke="var(--muted)" />
                  <Tooltip formatter={(v) => signed(v)} cursor={{ fill: "rgba(99,102,241,.08)" }} contentStyle={tip} />
                  <Bar dataKey="pnl" radius={[6, 6, 0, 0]}>
                    {pnlBars.map((d) => <Cell key={d.symbol} fill={d.pnl >= 0 ? "#10b981" : "#f43f5e"} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section className="panel">
            <h2>Current holdings</h2>
            {holdings.length ? (
              <div className="scroll"><table>
                <thead><tr><th>Stock</th><th className="r">Shares</th><th className="r">Avg cost</th><th className="r">Last price</th><th className="r">Value</th><th className="r">Unrealised P&L</th><th /></tr></thead>
                <tbody>{holdings.map((h) => (
                  <tr key={h.symbol}>
                    <td><Ticker symbol={h.symbol} /></td>
                    <td className="r">{h.quantity}</td>
                    <td className="r">{inr(h.avg_cost)}</td>
                    <td className="r">{inr(h.ltp)}{!h.live && <small className="muted" title="Live quote unavailable, showing your average cost"> (est.)</small>}</td>
                    <td className="r">{inr(h.value)}</td>
                    <td className="r"><span className={`pill ${tone(h.unrealized)}`}>{signed(h.unrealized)} · {pct(h.unrealized_pct)}</span></td>
                    <td className="r"><button className="btn tiny" onClick={() => setModal({ symbol: h.symbol, side: "sell" })}>Sell</button></td>
                  </tr>))}
                </tbody></table></div>
            ) : <p className="muted">Nothing held right now.</p>}
          </section>

          <section className="panel">
            <h2>Every stock you have traded</h2>
            <div className="scroll"><table>
              <thead><tr><th>Stock</th><th>Status</th><th className="r">Trades</th><th className="r">Booked P&L</th></tr></thead>
              <tbody>{history.map((h) => (
                <tr key={h.symbol}><td><Ticker symbol={h.symbol} /></td>
                  <td><span className={`tag ${h.status === "open" ? "open" : "closed"}`}>{h.status === "open" ? "Still holding" : "Fully sold"}</span></td>
                  <td className="r">{h.trades}</td>
                  <td className="r"><span className={`pill ${tone(h.realized)}`}>{signed(h.realized)}</span></td></tr>))}
              </tbody></table></div>
          </section>

          <section className="panel">
            <h2>Trade history</h2>
            <div className="scroll"><table>
              <thead><tr><th>Date</th><th>Stock</th><th>Side</th><th className="r">Shares</th><th className="r">Price</th><th className="r">Charges</th><th>Note</th><th /></tr></thead>
              <tbody>{trades.map((x) => (
                <tr key={x.id}><td>{x.trade_date}</td><td><Ticker symbol={x.symbol} /></td>
                  <td><span className={`tag ${x.side}`}>{x.side === "buy" ? "Bought" : "Sold"}</span></td>
                  <td className="r">{x.quantity}</td><td className="r">{inr(x.price)}</td><td className="r">{inr(x.fees)}</td>
                  <td className="muted">{x.notes}</td>
                  <td className="r"><button className="btn tiny ghost" onClick={() => remove(x.id)} aria-label={`Delete ${x.symbol} trade`}>Delete</button></td></tr>))}
              </tbody></table></div>
          </section>
        </>
      )}

      {modal && <TradeModal preset={modal === true ? null : modal} onClose={() => setModal(false)} onSaved={() => { setModal(false); load(); }} />}
    </>
  );
}

const Stat = ({ icon, c, label, value, sub, meter }) => (
  <div className={`stat ${c}`}>
    <span className="ico"><Icon name={icon} /></span>
    <div>
      <span className="muted">{label}</span>
      <b>{value}</b>
      {sub && <small className="muted">{sub}</small>}
      {meter != null && <div className="meter"><i style={{ width: `${Math.min(meter, 100)}%` }} /></div>}
    </div>
  </div>
);
