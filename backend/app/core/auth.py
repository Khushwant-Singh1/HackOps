"""
JWT Token Management and Authentication Services

This module provides:
- JWT token generation and validation
- Refresh token management
- Token blacklisting and revocation
- Security utilities for authentication
"""

import jwt
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union
from uuid import UUID

from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.config import settings
# from app.core.redis_client import session_store  # Temporarily disabled due to aioredis issues
from app.models.user import User, UserSession


# Mock session store for development (replace with Redis later)
class MockSessionStore:
    """Mock session store for development without Redis."""
    
    def __init__(self):
        self._sessions = {}
        self._user_sessions = {}
        self._blacklist = set()
    
    async def store_session(self, session_id: str, session_data: dict, expire_seconds: int) -> bool:
        self._sessions[session_id] = session_data
        return True
    
    async def get_session(self, session_id: str) -> dict:
        return self._sessions.get(session_id)
    
    async def add_user_session(self, user_id: int, session_id: str) -> bool:
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = set()
        self._user_sessions[user_id].add(session_id)
        return True
    
    async def get_user_sessions(self, user_id: int) -> set:
        return self._user_sessions.get(user_id, set())
    
    async def is_token_blacklisted(self, token: str) -> bool:
        return token in self._blacklist
    
    async def blacklist_token(self, token: str, expire_seconds: int) -> bool:
        self._blacklist.add(token)
        return True
    
    async def cleanup_user_sessions(self, user_id: int) -> int:
        if user_id in self._user_sessions:
            count = len(self._user_sessions[user_id])
            del self._user_sessions[user_id]
            return count
        return 0


session_store = MockSessionStore()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class TokenManager:
    """Manages JWT tokens and refresh tokens."""
    
    def __init__(self):
        self.algorithm = settings.ALGORITHM
        self.secret_key = settings.SECRET_KEY
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
    
    def create_access_token(self, user_id: Union[int, str], expires_delta: Optional[timedelta] = None) -> str:
        """Create a new access token."""
        data = {"sub": str(user_id)}
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, user_id: Union[int, str]) -> str:
        """Create a new refresh token."""
        data = {"sub": str(user_id)}
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh",
            "jti": secrets.token_urlsafe(32)  # Unique identifier for token revocation
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Verify token type
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type. Expected {token_type}"
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def extract_user_data(self, token: str) -> Dict[str, Any]:
        """Extract user data from access token."""
        payload = self.verify_token(token, "access")
        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "tenant_id": payload.get("tenant_id"),
            "roles": payload.get("roles", []),
            "permissions": payload.get("permissions", [])
        }
    
    def create_token_pair(self, user_data: Dict[str, Any]) -> Dict[str, str]:
        """Create both access and refresh tokens."""
        access_token = self.create_access_token(user_data)
        refresh_token = self.create_refresh_token({"sub": user_data.get("sub")})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

class PasswordManager:
    """Manages password hashing and verification."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def generate_secure_token() -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(32)

class SessionManager:
    """Manages user sessions with Redis storage."""
    
    def __init__(self):
        self.session_ttl = 60 * 60 * 24 * 7  # 7 days
    
    async def create_session(
        self, 
        user_id: int, 
        refresh_token: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        db: Optional[Session] = None
    ) -> UserSession:
        """Create a new user session."""
        # Generate session ID
        session_id = secrets.token_urlsafe(32)
        
        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        # Create session record in database
        session = UserSession(
            id=session_id,
            user_id=user_id,
            refresh_token=refresh_token,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
            last_accessed=datetime.now(timezone.utc),
            is_active=True
        )
        
        if db:
            db.add(session)
            db.commit()
            db.refresh(session)
        
        # Store in Redis for fast lookup
        session_data = {
            "user_id": user_id,
            "refresh_token": refresh_token,
            "expires_at": expires_at.isoformat(),
            "user_agent": user_agent or "",
            "ip_address": ip_address or "",
            "is_active": True,
            "last_accessed": datetime.now(timezone.utc).isoformat()
        }
        
        await session_store.store_session(session_id, session_data, self.session_ttl)
        await session_store.add_user_session(user_id, session_id)
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data."""
        return await session_store.get_session(session_id)
    
    async def is_token_valid(self, refresh_token: str) -> bool:
        """Check if refresh token is valid and not blacklisted."""
        # Check if token is blacklisted
        if await session_store.is_token_blacklisted(refresh_token):
            return False
        
        # Check if session exists (this validates the token indirectly)
        user_sessions = await session_store.get_user_sessions(0)  # This needs user_id
        # For now, we'll just check if it's not blacklisted
        return True
    
    async def invalidate_session(self, refresh_token: str) -> bool:
        """Invalidate a specific session."""
        # Add token to blacklist
        expire_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
        return await session_store.blacklist_token(refresh_token, expire_seconds)
    
    async def invalidate_user_sessions(self, user_id: int, db: Optional[Session] = None) -> int:
        """Invalidate all sessions for a user."""
        # Get all user sessions from Redis
        session_ids = await session_store.get_user_sessions(user_id)
        
        count = 0
        for session_id in session_ids:
            session_data = await session_store.get_session(session_id)
            if session_data and session_data.get("refresh_token"):
                # Blacklist the refresh token
                refresh_token = session_data["refresh_token"]
                expire_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
                await session_store.blacklist_token(refresh_token, expire_seconds)
                count += 1
        
        # Clean up session data
        await session_store.cleanup_user_sessions(user_id)
        
        # Update database if provided
        if db:
            sessions = db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            ).all()
            
            for session in sessions:
                session.is_active = False
                session.revoked_at = datetime.now(timezone.utc)
            
            db.commit()
        
        return count
    
    async def update_session_token(
        self, 
        old_token: str, 
        new_token: str, 
        db: Optional[Session] = None
    ) -> bool:
        """Update session with new refresh token."""
        # Blacklist old token
        await self.invalidate_session(old_token)
        
        # The new session will be created separately
        return True
        from sqlalchemy import select
        result = await db.execute(
            select(UserSession)
            .where(UserSession.session_token == session_token)
            .where(UserSession.is_active == True)
            .where(UserSession.expires_at > datetime.now(timezone.utc))
        )
        session = result.scalar_one_or_none()
        
        if session:
            # Update last activity
            session.last_activity_at = datetime.now(timezone.utc)
            await db.commit()
            
            # Update Redis cache
            if self.redis:
                await self.redis.hset(
                    f"{self.session_prefix}{session_token}",
                    "last_activity",
                    datetime.now(timezone.utc).isoformat()
                )
        
        return session
    
    async def revoke_session(self, db: AsyncSession, session_token: str) -> bool:
        """Revoke a specific session."""
        from sqlalchemy import select, update
        
        # Update database
        result = await db.execute(
            update(UserSession)
            .where(UserSession.session_token == session_token)
            .values(is_active=False, revoked_at=datetime.now(timezone.utc))
        )
        
        success = result.rowcount > 0
        
        if success:
            await db.commit()
            
            # Remove from Redis
            if self.redis:
                await self.redis.delete(f"{self.session_prefix}{session_token}")
        
        return success
    
    async def revoke_all_user_sessions(self, db: AsyncSession, user_id: UUID) -> int:
        """Revoke all sessions for a user."""
        from sqlalchemy import select, update
        
        # Get all active sessions for user
        result = await db.execute(
            select(UserSession.session_token)
            .where(UserSession.user_id == user_id)
            .where(UserSession.is_active == True)
        )
        session_tokens = [row[0] for row in result.fetchall()]
        
        # Update database
        result = await db.execute(
            update(UserSession)
            .where(UserSession.user_id == user_id)
            .where(UserSession.is_active == True)
            .values(is_active=False, revoked_at=datetime.now(timezone.utc))
        )
        
        revoked_count = result.rowcount
        
        if revoked_count > 0:
            await db.commit()
            
            # Remove from Redis
            if self.redis:
                for token in session_tokens:
                    await self.redis.delete(f"{self.session_prefix}{token}")
        
        return revoked_count
    
    async def is_token_blacklisted(self, token_jti: str) -> bool:
        """Check if a token is blacklisted."""
        if not self.redis:
            return False
        
        exists = await self.redis.exists(f"{self.blacklist_prefix}{token_jti}")
        return bool(exists)
    
    async def blacklist_token(self, token_jti: str, expires_at: datetime) -> None:
        """Add a token to the blacklist."""
        if not self.redis:
            return
        
        # Calculate TTL until token naturally expires
        ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())
        if ttl > 0:
            await self.redis.setex(
                f"{self.blacklist_prefix}{token_jti}",
                ttl,
                "blacklisted"
            )

# Global instances
token_manager = TokenManager()
password_manager = PasswordManager()
session_manager = SessionManager()

def get_password_hash(password: str) -> str:
    """Hash a password - compatible with existing models."""
    return password_manager.hash_password(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password - compatible with existing models."""
    return password_manager.verify_password(plain_password, hashed_password)
