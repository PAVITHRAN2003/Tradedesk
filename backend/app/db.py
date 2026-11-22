from motor.motor_asyncio import AsyncIOMotorClient

from .config import settings

client = AsyncIOMotorClient(settings.mongo_url)
db = client[settings.mongo_db]


async def init_db():
    await db.users.create_index("email", unique=True)
    await db.refresh_tokens.create_index("token_hash", unique=True)
    await db.refresh_tokens.create_index("expires_at", expireAfterSeconds=0)  # TTL cleanup
    await db.trades.create_index([("user_id", 1), ("trade_date", -1)])
    await db.agent_runs.create_index([("user_id", 1), ("created_at", -1)])
    # runs that were in flight when the server stopped can never finish
    await db.agent_runs.update_many(
        {"status": "running"}, {"$set": {"status": "error", "error": "Server restarted"}}
    )
