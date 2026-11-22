from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from ..db import db
from ..deps import get_current_user
from ..quotes import get_quotes
from ..utils import oid, utcnow

router = APIRouter(prefix="/api", tags=["portfolio"])


class TradeIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    side: Literal["buy", "sell"]
    quantity: int = Field(gt=0)
    price: float = Field(gt=0)
    fees: float = Field(default=0, ge=0)
    trade_date: date
    notes: str = Field(default="", max_length=300)

    @field_validator("symbol")
    @classmethod
    def normalise(cls, v: str) -> str:
        v = v.strip().upper()
        return v[:-3] if v.endswith(".NS") else v


def trade_out(t) -> dict:
    return {"id": str(t["_id"]), "symbol": t["symbol"], "side": t["side"],
            "quantity": t["quantity"], "price": t["price"], "fees": t.get("fees", 0),
            "trade_date": t["trade_date"].date().isoformat(), "notes": t.get("notes", "")}


def compute_positions(trades: list[dict]):
    """Average-cost accounting. Returns per-symbol positions and a list of realised P&L per sell."""
    pos: dict[str, dict] = {}
    sell_pnls: list[float] = []
    for t in sorted(trades, key=lambda t: (t["trade_date"], t["created_at"])):
        p = pos.setdefault(t["symbol"], {"symbol": t["symbol"], "qty": 0, "cost": 0.0,
                                          "realized": 0.0, "trades": 0})
        p["trades"] += 1
        qty, fees = t["quantity"], t.get("fees", 0)
        if t["side"] == "buy":
            p["qty"] += qty
            p["cost"] += qty * t["price"] + fees
        else:
            qty = min(qty, p["qty"])
            if qty <= 0:
                continue
            avg = p["cost"] / p["qty"]
            pnl = qty * t["price"] - fees - avg * qty
            p["realized"] += pnl
            sell_pnls.append(pnl)
            p["cost"] -= avg * qty
            p["qty"] -= qty
    return pos, sell_pnls


@router.get("/trades")
async def list_trades(user=Depends(get_current_user)):
    cursor = db.trades.find({"user_id": user["_id"]}).sort([("trade_date", -1), ("created_at", -1)])
    return [trade_out(t) async for t in cursor]


@router.post("/trades", status_code=201)
async def add_trade(body: TradeIn, user=Depends(get_current_user)):
    if body.side == "sell":
        existing = [t async for t in db.trades.find({"user_id": user["_id"], "symbol": body.symbol})]
        pos, _ = compute_positions(existing)
        held = pos.get(body.symbol, {}).get("qty", 0)
        if body.quantity > held:
            raise HTTPException(400, f"You only hold {held} shares of {body.symbol}")
    doc = {**body.model_dump(), "user_id": user["_id"], "created_at": utcnow(),
           "trade_date": datetime.combine(body.trade_date, datetime.min.time())}
    res = await db.trades.insert_one(doc)
    doc["_id"] = res.inserted_id
    return trade_out(doc)


@router.delete("/trades/{trade_id}", status_code=204)
async def delete_trade(trade_id: str, user=Depends(get_current_user)):
    res = await db.trades.delete_one({"_id": oid(trade_id), "user_id": user["_id"]})
    if not res.deleted_count:
        raise HTTPException(404, "Trade not found")


@router.get("/portfolio/summary")
async def summary(user=Depends(get_current_user)):
    trades = [t async for t in db.trades.find({"user_id": user["_id"]})]
    pos, sell_pnls = compute_positions(trades)
    open_syms = [s for s, p in pos.items() if p["qty"] > 0]
    quotes = await get_quotes(open_syms) if open_syms else {}

    holdings = []
    for s in open_syms:
        p = pos[s]
        avg = p["cost"] / p["qty"]
        live = s in quotes
        ltp = quotes.get(s, avg)
        value = p["qty"] * ltp
        unreal = value - p["cost"]
        holdings.append({
            "symbol": s, "quantity": p["qty"], "avg_cost": round(avg, 2), "ltp": round(ltp, 2),
            "live": live, "invested": round(p["cost"], 2), "value": round(value, 2),
            "unrealized": round(unreal, 2),
            "unrealized_pct": round(unreal / p["cost"] * 100, 2) if p["cost"] else 0,
        })
    holdings.sort(key=lambda h: h["value"], reverse=True)

    history = [{"symbol": s, "realized": round(p["realized"], 2), "trades": p["trades"],
                "status": "open" if p["qty"] > 0 else "closed"} for s, p in pos.items()]
    history.sort(key=lambda h: h["realized"], reverse=True)

    invested = sum(h["invested"] for h in holdings)
    value = sum(h["value"] for h in holdings)
    realized = sum(p["realized"] for p in pos.values())
    wins = sum(1 for x in sell_pnls if x > 0)
    return {
        "totals": {
            "invested": round(invested, 2), "value": round(value, 2),
            "unrealized": round(value - invested, 2), "realized": round(realized, 2),
            "total_pnl": round(value - invested + realized, 2),
            "win_rate": round(wins / len(sell_pnls) * 100, 1) if sell_pnls else None,
            "trade_count": len(trades), "symbols_traded": len(pos),
        },
        "holdings": holdings, "history": history,
    }
