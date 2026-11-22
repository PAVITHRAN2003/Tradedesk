"""Exact indicators (yfinance) for the specific tickers the web search picked. No fixed stock list."""
import asyncio
import json

import pandas as pd
import yfinance as yf
from langchain_core.tools import tool

def _r(x, n=2):
    return None if x is None or pd.isna(x) else round(float(x), n)


def _clean(sym: str) -> str:
    s = sym.strip().upper()
    return s[:-3] if s.endswith(".NS") else s


def _rsi(close: pd.Series, n: int = 14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + gain / loss)


def metrics(sym: str, d: pd.DataFrame) -> dict:
    """Pure function: daily OHLCV frame -> indicator dict."""
    d = d.dropna(subset=["Close"])
    if len(d) < 30:
        return {"ticker": sym, "error": "not enough price history"}
    c, v = d["Close"], d["Volume"]

    def chg(n):
        return _r((c.iloc[-1] / c.iloc[-1 - n] - 1) * 100) if len(c) > n else None

    daily = c.pct_change().dropna()
    return {
        "ticker": sym,
        "as_of": str(d.index[-1].date()),
        "last_close": _r(c.iloc[-1]),
        "prev_close": _r(c.iloc[-2]),
        "change_1d_pct": chg(1), "change_7d_pct": chg(5), "change_30d_pct": chg(21),
        "volume": int(v.iloc[-1]),
        "volume_vs_20d_avg": _r(v.iloc[-1] / v.iloc[-21:-1].mean()),
        "rsi14": _r(_rsi(c).iloc[-1], 1),
        "sma50": _r(c.rolling(50).mean().iloc[-1]) if len(c) >= 50 else None,
        "sma200": _r(c.rolling(200).mean().iloc[-1]) if len(c) >= 200 else None,
        "high_52w": _r(c.max()), "low_52w": _r(c.min()),
        "volatility_spike": bool(len(daily) >= 60 and daily.iloc[-5:].std() > 1.5 * daily.iloc[-60:].std()),
    }


def _market_data(symbols: list[str]) -> str:
    out = []
    for s in symbols[:5]:
        try:
            out.append(metrics(s, yf.Ticker(f"{s}.NS").history(period="1y", interval="1d", auto_adjust=True)))
        except Exception as e:
            out.append({"ticker": s, "error": str(e)[:120]})
    return json.dumps(out)


@tool
async def get_market_data(tickers: list[str]) -> str:
    """Get real market data for up to 5 NSE tickers (e.g. ["RELIANCE", "INFY"]): last and previous close,
    1/5/21-day change %, volume vs 20-day average, RSI14, 50 and 200-day moving averages, 52-week range,
    volatility spike flag and the as_of trading date. Call this ONCE with all tickers."""
    return await asyncio.to_thread(_market_data, [_clean(t) for t in tickers])