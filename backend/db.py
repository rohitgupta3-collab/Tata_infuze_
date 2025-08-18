from __future__ import annotations
import os
from typing import Any
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

_MONGO_CLIENT: AsyncIOMotorClient | None = None

def _mongo_uri() -> str:
    return os.getenv("MONGODB_URI") or os.getenv("MONGO_URI") or "mongodb://localhost:27017"

def _db_name() -> str:
    return os.getenv("MONGODB_DB", "warehouse")

async def get_db() -> Any:
    '''
    Fast API dependency to get the DB Handle
    '''
    global _MONGO_CLIENT
    if _MONGO_CLIENT is None:
        _MONGO_CLIENT = AsyncIOMotorClient(_mongo_uri())
        
    return _MONGO_CLIENT[_db_name()]

async def init_indexes(db) -> None:
    await db.medicines.create_index("id", unique = True)
    await db.medicines.create_index("category")
    await db.medicines.create_index("bin")