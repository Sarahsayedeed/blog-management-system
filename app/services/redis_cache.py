# app/services/redis_cache.py
import json
import redis.asyncio as redis
from typing import Any, Optional
from fastapi.encoders import jsonable_encoder
from app.config import settings

redis_db = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

async def check_redis_connection():
    try:
        await redis_db.ping()
        print("✅ Redis connected successfully!")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")

async def get_cache(key: str) -> Optional[Any]:
    try:
        data = await redis_db.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        print(f"Redis GET Error: {e}")
        return None

async def set_cache(key: str, value: Any, expire: int = 3600):
    try:
        print(f"DEBUG: Attempting to save key '{key}' to Redis...") 
        json_value = json.dumps(jsonable_encoder(value))
        await redis_db.set(key, json_value, ex=expire)
        print(f"DEBUG: Key '{key}' saved successfully!")
    except Exception as e:
        print(f"Redis SET Error: {e}")

async def delete_cache(key: str):
    try:
        await redis_db.delete(key)
    except Exception as e:
        print(f"Redis DELETE Error: {e}")

async def delete_cache_pattern(pattern: str):
    try:
        keys = await redis_db.keys(pattern)
        if keys:
            await redis_db.delete(*keys)
    except Exception as e:
        print(f"Redis DELETE PATTERN Error: {e}")