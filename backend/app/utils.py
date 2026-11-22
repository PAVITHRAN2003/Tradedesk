from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException


def utcnow() -> datetime:
    """Naive UTC (what Mongo hands back), so comparisons never mix aware/naive."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(404, "Not found")
