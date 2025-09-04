"""
Redis client configuration and utilities for session management.
"""

import aioredis
from typing import Optional, Any
import json
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper with connection management."""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self._connection_pool: Optional[aioredis.ConnectionPool] = None
    
    async def connect(self) -> None:
        """Establish Redis connection."""
        try:
            self._connection_pool = aioredis.ConnectionPool.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20
            )
            self.redis = aioredis.Redis(connection_pool=self._connection_pool)
            
            # Test connection
            await self.redis.ping()
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
        if self._connection_pool:
            await self._connection_pool.disconnect()
        logger.info("Redis connection closed")
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        if not self.redis:
            raise RuntimeError("Redis client not connected")
        
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: str, 
        expire: Optional[int] = None
    ) -> bool:
        """Set key-value pair with optional expiration."""
        if not self.redis:
            raise RuntimeError("Redis client not connected")
        
        try:
            result = await self.redis.set(key, value, ex=expire)
            return result is True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key."""
        if not self.redis:
            raise RuntimeError("Redis client not connected")
        
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.redis:
            raise RuntimeError("Redis client not connected")
        
        try:
            result = await self.redis.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    async def set_json(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[int] = None
    ) -> bool:
        """Set JSON value."""
        try:
            json_value = json.dumps(value)
            return await self.set(key, json_value, expire)
        except (TypeError, ValueError) as e:
            logger.error(f"JSON serialization error for key {key}: {e}")
            return False
    
    async def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value."""
        try:
            value = await self.get(key)
            if value is None:
                return None
            return json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"JSON deserialization error for key {key}: {e}")
            return None
    
    async def sadd(self, key: str, *values: str) -> int:
        """Add values to set."""
        if not self.redis:
            raise RuntimeError("Redis client not connected")
        
        try:
            return await self.redis.sadd(key, *values)
        except Exception as e:
            logger.error(f"Redis SADD error for key {key}: {e}")
            return 0
    
    async def srem(self, key: str, *values: str) -> int:
        """Remove values from set."""
        if not self.redis:
            raise RuntimeError("Redis client not connected")
        
        try:
            return await self.redis.srem(key, *values)
        except Exception as e:
            logger.error(f"Redis SREM error for key {key}: {e}")
            return 0
    
    async def sismember(self, key: str, value: str) -> bool:
        """Check if value is member of set."""
        if not self.redis:
            raise RuntimeError("Redis client not connected")
        
        try:
            result = await self.redis.sismember(key, value)
            return result
        except Exception as e:
            logger.error(f"Redis SISMEMBER error for key {key}: {e}")
            return False
    
    async def smembers(self, key: str) -> set:
        """Get all members of set."""
        if not self.redis:
            raise RuntimeError("Redis client not connected")
        
        try:
            return await self.redis.smembers(key)
        except Exception as e:
            logger.error(f"Redis SMEMBERS error for key {key}: {e}")
            return set()
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key."""
        if not self.redis:
            raise RuntimeError("Redis client not connected")
        
        try:
            result = await self.redis.expire(key, seconds)
            return result
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get TTL for key."""
        if not self.redis:
            raise RuntimeError("Redis client not connected")
        
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL error for key {key}: {e}")
            return -1


# Global Redis client instance
redis_client = RedisClient()


# Session management utilities
class SessionStore:
    """Redis-based session store."""
    
    def __init__(self, client: RedisClient):
        self.client = client
        self.session_prefix = "session:"
        self.user_sessions_prefix = "user_sessions:"
        self.blacklist_prefix = "blacklist:"
    
    async def store_session(
        self, 
        session_id: str, 
        session_data: dict, 
        expire_seconds: int
    ) -> bool:
        """Store session data."""
        key = f"{self.session_prefix}{session_id}"
        return await self.client.set_json(key, session_data, expire_seconds)
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data."""
        key = f"{self.session_prefix}{session_id}"
        return await self.client.get_json(key)
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        key = f"{self.session_prefix}{session_id}"
        return await self.client.delete(key)
    
    async def add_user_session(self, user_id: int, session_id: str) -> bool:
        """Add session to user's session set."""
        key = f"{self.user_sessions_prefix}{user_id}"
        result = await self.client.sadd(key, session_id)
        # Set expiration for user sessions set (7 days)
        await self.client.expire(key, 7 * 24 * 3600)
        return result > 0
    
    async def remove_user_session(self, user_id: int, session_id: str) -> bool:
        """Remove session from user's session set."""
        key = f"{self.user_sessions_prefix}{user_id}"
        result = await self.client.srem(key, session_id)
        return result > 0
    
    async def get_user_sessions(self, user_id: int) -> set:
        """Get all sessions for user."""
        key = f"{self.user_sessions_prefix}{user_id}"
        return await self.client.smembers(key)
    
    async def blacklist_token(self, token: str, expire_seconds: int) -> bool:
        """Add token to blacklist."""
        key = f"{self.blacklist_prefix}{token}"
        return await self.client.set(key, "1", expire_seconds)
    
    async def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted."""
        key = f"{self.blacklist_prefix}{token}"
        return await self.client.exists(key)
    
    async def cleanup_user_sessions(self, user_id: int) -> int:
        """Clean up all sessions for user."""
        sessions = await self.get_user_sessions(user_id)
        count = 0
        
        for session_id in sessions:
            if await self.delete_session(session_id):
                count += 1
        
        # Clear user sessions set
        user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
        await self.client.delete(user_sessions_key)
        
        return count


# Global session store instance
session_store = SessionStore(redis_client)
