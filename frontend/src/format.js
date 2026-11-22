const inrFmt = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 });
const shortFmt = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", notation: "compact", maximumFractionDigits: 1 });
export const inr = (n) => (n == null ? "–" : inrFmt.format(n));
export const inrShort = (n) => (n == null ? "–" : shortFmt.format(n));
export const signed = (n) => (n > 0 ? "+" : "") + inr(n);
export const pct = (n) => (n == null ? "–" : `${n > 0 ? "+" : ""}${n.toFixed(2)}%`);
export const tone = (n) => (n > 0 ? "gain" : n < 0 ? "loss" : "");
