"""
Authentication endpoints for the HackOps API.
Handles login, logout, registration, OAuth flows, and token management.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import TokenManager, PasswordManager, SessionManager
from app.core.oauth import OAuthManager
from app.core.dependencies import get_current_user, get_current_active_user
from app.models.user import User
from app.models.user_session import UserSession

router = APIRouter()
security = HTTPBearer()
token_manager = TokenManager()
password_manager = PasswordManager()
session_manager = SessionManager()
oauth_manager = OAuthManager()


# Request/Response Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    display_name: Optional[str] = None


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr


class OAuthCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


# Authentication Endpoints
@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """Login with email and password."""
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is disabled")
    
    # Verify password
    if not password_manager.verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate tokens
    access_token = token_manager.create_access_token(user.id)
    refresh_token = token_manager.create_refresh_token(user.id)
    
    # Create session
    user_agent = http_request.headers.get("user-agent", "") if http_request else ""
    ip_address = http_request.client.host if http_request else ""
    
    session = await session_manager.create_session(
        user_id=user.id,
        refresh_token=refresh_token,
        user_agent=user_agent,
        ip_address=ip_address,
        db=db
    )
    
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=token_manager.access_token_expire_minutes * 60,
        user={
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "system_role": user.system_role,
            "is_verified": user.is_verified
        }
    )


@router.post("/register", response_model=AuthResponse)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """Register a new user account."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    password_hash = password_manager.hash_password(request.password)
    user = User(
        email=request.email,
        password_hash=password_hash,
        first_name=request.first_name,
        last_name=request.last_name,
        display_name=request.display_name or f"{request.first_name} {request.last_name}",
        is_active=True,
        is_verified=False  # Users need to verify their email
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Generate tokens
    access_token = token_manager.create_access_token(user.id)
    refresh_token = token_manager.create_refresh_token(user.id)
    
    # Create session
    user_agent = http_request.headers.get("user-agent", "") if http_request else ""
    ip_address = http_request.client.host if http_request else ""
    
    session = await session_manager.create_session(
        user_id=user.id,
        refresh_token=refresh_token,
        user_agent=user_agent,
        ip_address=ip_address,
        db=db
    )
    
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=token_manager.access_token_expire_minutes * 60,
        user={
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "system_role": user.system_role,
            "is_verified": user.is_verified
        }
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    try:
        # Verify refresh token
        payload = token_manager.verify_token(request.refresh_token)
        user_id = payload.get("sub")
        
        # Check if refresh token is valid and not blacklisted
        if not await session_manager.is_token_valid(request.refresh_token):
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        
        # Generate new tokens
        access_token = token_manager.create_access_token(user.id)
        new_refresh_token = token_manager.create_refresh_token(user.id)
        
        # Update session with new refresh token
        await session_manager.update_session_token(
            old_token=request.refresh_token,
            new_token=new_refresh_token,
            db=db
        )
        
        return AuthResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=token_manager.access_token_expire_minutes * 60,
            user={
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "system_role": user.system_role,
                "is_verified": user.is_verified
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Logout current user and invalidate session."""
    await session_manager.invalidate_user_sessions(current_user.id, db)
    return {"message": "Successfully logged out"}


@router.post("/logout-all")
async def logout_all(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Logout from all devices by invalidating all user sessions."""
    await session_manager.invalidate_user_sessions(current_user.id, db)
    return {"message": "Successfully logged out from all devices"}


# OAuth Endpoints
@router.get("/oauth/{provider}/url")
async def get_oauth_url(provider: str):
    """Get OAuth authorization URL for the specified provider."""
    try:
        auth_url = oauth_manager.get_authorization_url(provider)
        return {"authorization_url": auth_url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/oauth/{provider}/callback", response_model=AuthResponse)
async def oauth_callback(
    provider: str,
    request: OAuthCallbackRequest,
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """Handle OAuth callback and authenticate user."""
    try:
        # Exchange code for user info
        user_info = await oauth_manager.exchange_code_for_user_info(provider, request.code)
        
        # Find or create user
        user = db.query(User).filter(
            User.email == user_info.email
        ).first()
        
        if user:
            # Update existing user with OAuth info
            user.auth_provider = provider
            user.oauth_id = user_info.id
            user.avatar_url = user_info.avatar_url or user.avatar_url
            user.is_verified = True  # OAuth users are considered verified
        else:
            # Create new user
            user = User(
                email=user_info.email,
                first_name=user_info.first_name,
                last_name=user_info.last_name,
                display_name=user_info.name,
                avatar_url=user_info.avatar_url,
                auth_provider=provider,
                oauth_id=user_info.id,
                is_active=True,
                is_verified=True
            )
            db.add(user)
        
        db.commit()
        db.refresh(user)
        
        # Generate tokens
        access_token = token_manager.create_access_token(user.id)
        refresh_token = token_manager.create_refresh_token(user.id)
        
        # Create session
        user_agent = http_request.headers.get("user-agent", "") if http_request else ""
        ip_address = http_request.client.host if http_request else ""
        
        session = await session_manager.create_session(
            user_id=user.id,
            refresh_token=refresh_token,
            user_agent=user_agent,
            ip_address=ip_address,
            db=db
        )
        
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=token_manager.access_token_expire_minutes * 60,
            user={
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "system_role": user.system_role,
                "is_verified": user.is_verified
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth authentication failed: {str(e)}")


# Password Management
@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change user password."""
    # Verify current password
    if not password_manager.verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Update password
    new_password_hash = password_manager.hash_password(request.new_password)
    current_user.password_hash = new_password_hash
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Invalidate all sessions to force re-login
    await session_manager.invalidate_user_sessions(current_user.id, db)
    
    return {"message": "Password changed successfully"}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """Request password reset (placeholder for email-based reset)."""
    # TODO: Implement email-based password reset
    # This would typically:
    # 1. Generate a secure reset token
    # 2. Store it in the database with expiration
    # 3. Send reset email to user
    # 4. Provide endpoint to verify token and reset password
    
    return {"message": "Password reset instructions sent to email"}


# User Info
@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "display_name": current_user.display_name,
        "avatar_url": current_user.avatar_url,
        "bio": current_user.bio,
        "phone_number": current_user.phone_number,
        "system_role": current_user.system_role,
        "is_verified": current_user.is_verified,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at
    }


@router.get("/sessions")
async def get_user_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's active sessions."""
    sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active == True
    ).all()
    
    return {
        "sessions": [
            {
                "id": session.id,
                "user_agent": session.user_agent,
                "ip_address": session.ip_address,
                "created_at": session.created_at,
                "last_accessed": session.last_accessed,
                "is_current": session.refresh_token == current_user.id  # This needs refinement
            }
            for session in sessions
        ]
    }


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Revoke a specific session."""
    session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await session_manager.invalidate_session(session.refresh_token)
    session.is_active = False
    session.revoked_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Session revoked successfully"}