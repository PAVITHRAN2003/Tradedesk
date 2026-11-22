import { useState } from "react";
import api, { errMsg } from "../api";

// local calendar date (toISOString would give the UTC date, which is "tomorrow" on a US evening)
const today = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);

export default function TradeModal({ onClose, onSaved, preset }) {
  const [f, setF] = useState({ symbol: preset?.symbol || "", side: preset?.side || "buy", quantity: "", price: "", fees: "0", trade_date: today(), notes: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      await api.post("/trades", { ...f, quantity: parseInt(f.quantity, 10), price: parseFloat(f.price), fees: parseFloat(f.fees || 0) });
      onSaved();
    } catch (x) { setErr(errMsg(x)); setBusy(false); }
  };

  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <form className="modal" onSubmit={submit}>
        <h2>Log a trade</h2>
        <div className="seg" role="radiogroup" aria-label="Side">
          {["buy", "sell"].map((s) => (
            <button type="button" key={s} role="radio" aria-checked={f.side === s} className={f.side === s ? `on ${s}` : ""}
              onClick={() => setF({ ...f, side: s })}>{s === "buy" ? "Bought" : "Sold"}</button>
          ))}
        </div>
        <div className="grid2">
          <label>NSE ticker<input required placeholder="RELIANCE" value={f.symbol} onChange={set("symbol")} /></label>
          <label>Date<input required type="date" max={today()} value={f.trade_date} onChange={set("trade_date")} /></label>
          <label>Shares<input required type="number" min="1" step="1" value={f.quantity} onChange={set("quantity")} /></label>
          <label>Price per share (₹)<input required type="number" min="0.01" step="0.01" value={f.price} onChange={set("price")} /></label>
          <label>Brokerage and charges (₹)<input type="number" min="0" step="0.01" value={f.fees} onChange={set("fees")} /></label>
          <label>Note<input maxLength={300} placeholder="Why you took it" value={f.notes} onChange={set("notes")} /></label>
        </div>
        {err && <div className="error" role="alert">{err}</div>}
        <div className="actions">
          <button type="button" className="btn ghost" onClick={onClose}>Cancel</button>
          <button className="btn primary" disabled={busy}>Save trade</button>
        </div>
      </form>
    </div>
  );
}
