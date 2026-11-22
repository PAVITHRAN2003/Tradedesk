"""Best-effort live prices for NSE symbols via yfinance, cached for 60s."""
import asyncio
import time

import yfinance as yf

_cache: dict[str, tuple[float, float]] = {}
TTL = 60


def _fetch(symbols: list[str]) -> dict[str, float]:
    out = {}
    for s in symbols:
        try:
            price = yf.Ticker(f"{s}.NS").fast_info.last_price
            if price:
                out[s] = float(price)
        except Exception:
            pass
    return out


async def get_quotes(symbols: list[str]) -> dict[str, float]:
    now = time.time()
    result = {s: _cache[s][0] for s in symbols if s in _cache and now - _cache[s][1] < TTL}
    missing = [s for s in symbols if s not in result]
    if missing:
        fresh = await asyncio.to_thread(_fetch, missing)
        for s, p in fresh.items():
            _cache[s] = (p, now)
        result.update(fresh)
    return result
