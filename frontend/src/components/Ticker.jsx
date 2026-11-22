// Coloured initials chip, hue derived from the symbol so each stock keeps its colour.
export default function Ticker({ symbol }) {
  let h = 0;
  for (const ch of symbol) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return (
    <span className="ticker">
      <i style={{ background: `linear-gradient(135deg, hsl(${h} 75% 52%), hsl(${(h + 45) % 360} 70% 42%))` }}>{symbol.slice(0, 2)}</i>
      {symbol}
    </span>
  );
}
