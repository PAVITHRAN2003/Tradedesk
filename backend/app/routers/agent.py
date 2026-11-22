import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..agent.stock_agent import run_stock_agent
from ..db import db
from ..deps import get_current_user
from ..utils import oid, utcnow

router = APIRouter(prefix="/api/agent", tags=["agent"])
_tasks: set[asyncio.Task] = set()  # keep references so tasks aren't garbage collected


class RunIn(BaseModel):
    query: str = Field(default="Give me good stock recommendation from NSE", max_length=500)


def run_out(r, full=True) -> dict:
    out = {"id": str(r["_id"]), "query": r["query"], "status": r["status"],
           "created_at": r["created_at"].isoformat() + "Z", "error": r.get("error")}
    if full:
        out.update(final=r.get("final", ""), steps=r.get("steps", []))
    return out


async def execute(run_id, query: str):
    try:
        out = await run_stock_agent(query)
        await db.agent_runs.update_one({"_id": run_id}, {"$set": {"status": "done", **out, "finished_at": utcnow()}})
    except Exception as e:  # surface the failure in the UI instead of hanging on "running"
        await db.agent_runs.update_one({"_id": run_id}, {"$set": {"status": "error", "error": str(e)[:500]}})


@router.post("/runs", status_code=202)
async def start_run(body: RunIn, user=Depends(get_current_user)):
    if await db.agent_runs.find_one({"user_id": user["_id"], "status": "running"}):
        raise HTTPException(409, "An analysis is already running")
    doc = {"user_id": user["_id"], "query": body.query, "status": "running", "created_at": utcnow()}
    res = await db.agent_runs.insert_one(doc)
    task = asyncio.create_task(execute(res.inserted_id, body.query))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    doc["_id"] = res.inserted_id
    return run_out(doc, full=False)


@router.get("/runs")
async def list_runs(user=Depends(get_current_user)):
    cur = db.agent_runs.find({"user_id": user["_id"]}).sort("created_at", -1).limit(20)
    return [run_out(r, full=False) async for r in cur]


@router.get("/runs/{run_id}")
async def get_run(run_id: str, user=Depends(get_current_user)):
    r = await db.agent_runs.find_one({"_id": oid(run_id), "user_id": user["_id"]})
    if not r:
        raise HTTPException(404, "Run not found")
    return run_out(r)
