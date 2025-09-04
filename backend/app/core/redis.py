"""
Redis connection and cache management
"""
import redis.asyncio as redis
from typing import Optional, Any, Union
import json
import pickle
from datetime import timedelta

from app.core.config import settings


class RedisManager:
    """Redis connection and cache manager"""
    
    def __init__(self):
        self.redis_pool: Optional[redis.ConnectionPool] = None
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Initialize Redis connection"""
        self.redis_pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20
        )
        self.redis_client = redis.Redis(connection_pool=self.redis_pool)
        
        # Test connection
        await self.redis_client.ping()
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
        if self.redis_pool:
            await self.redis_pool.disconnect()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        if not self.redis_client:
            return None
        
        value = await self.redis_client.get(key)
        if value is None:
            return None
        
        try:
            # Try to decode as JSON first
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            # Fallback to string
            return value
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """Set value in Redis"""
        if not self.redis_client:
            return False
        
        # Serialize value
        if isinstance(value, (dict, list)):
            serialized_value = json.dumps(value)
        else:
            serialized_value = str(value)
        
        return await self.redis_client.set(key, serialized_value, ex=expire)
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self.redis_client:
            return False
        
        result = await self.redis_client.delete(key)
        return result > 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        if not self.redis_client:
            return False
        
        return await self.redis_client.exists(key) > 0
    
    async def set_session(self, session_id: str, user_data: dict, expire: int = 3600):
        """Store user session data"""
        session_key = f"session:{session_id}"
        return await self.set(session_key, user_data, expire)
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve user session data"""
        session_key = f"session:{session_id}"
        return await self.get(session_key)
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete user session"""
        session_key = f"session:{session_id}"
        return await self.delete(session_key)
    
    async def cache_user_permissions(self, user_id: str, tenant_id: str, permissions: list):
        """Cache user permissions"""
        cache_key = f"permissions:{tenant_id}:{user_id}"
        return await self.set(cache_key, permissions, expire=1800)  # 30 minutes
    
    async def get_user_permissions(self, user_id: str, tenant_id: str) -> Optional[list]:
        """Get cached user permissions"""
        cache_key = f"permissions:{tenant_id}:{user_id}"
        return await self.get(cache_key)


# Global Redis manager instance
redis_manager = RedisManager()


async def get_redis() -> RedisManager:
    """Dependency to get Redis manager"""
    return redis_manager


async def init_redis():
    """Initialize Redis connection on startup"""
    await redis_manager.connect()


async def close_redis():
    """Close Redis connection on shutdown"""
    await redis_manager.disconnect()
