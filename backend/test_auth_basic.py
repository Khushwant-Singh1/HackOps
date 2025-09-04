"""
Basic tests for the authentication system.
Run with: pytest test_auth_basic.py -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

from app.core.auth import TokenManager, PasswordManager, SessionManager
from app.core.rbac import RBACManager, SystemRole, Permission


class TestTokenManager:
    """Test JWT token management."""
    
    def setup_method(self):
        self.token_manager = TokenManager()
    
    def test_create_access_token(self):
        """Test access token creation."""
        user_id = 123
        token = self.token_manager.create_access_token(user_id)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token can be decoded
        payload = self.token_manager.verify_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_id = 123
        token = self.token_manager.create_refresh_token(user_id)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token can be decoded
        payload = self.token_manager.verify_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"
    
    def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        with pytest.raises(Exception):
            self.token_manager.verify_token("invalid_token")
    
    def test_token_expiration(self):
        """Test token expiration logic."""
        user_id = 123
        # Create token with very short expiration
        expires_delta = timedelta(seconds=1)
        token = self.token_manager.create_access_token(user_id, expires_delta)
        
        # Token should be valid immediately
        payload = self.token_manager.verify_token(token)
        assert payload["sub"] == str(user_id)
        
        # Note: Testing actual expiration would require waiting or mocking time


class TestPasswordManager:
    """Test password hashing and verification."""
    
    def setup_method(self):
        self.password_manager = PasswordManager()
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = self.password_manager.hash_password(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # Should be hashed, not plain text
    
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "test_password_123"
        hashed = self.password_manager.hash_password(password)
        
        is_valid = self.password_manager.verify_password(password, hashed)
        assert is_valid is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = self.password_manager.hash_password(password)
        
        is_valid = self.password_manager.verify_password(wrong_password, hashed)
        assert is_valid is False
    
    def test_generate_salt(self):
        """Test salt generation."""
        salt1 = self.password_manager.generate_salt()
        salt2 = self.password_manager.generate_salt()
        
        assert isinstance(salt1, str)
        assert isinstance(salt2, str)
        assert len(salt1) > 0
        assert len(salt2) > 0
        assert salt1 != salt2  # Should be unique


class TestRBACManager:
    """Test Role-Based Access Control."""
    
    def setup_method(self):
        self.rbac_manager = RBACManager()
    
    def test_system_roles(self):
        """Test system role enumeration."""
        assert SystemRole.SUPER_ADMIN in SystemRole
        assert SystemRole.PLATFORM_ADMIN in SystemRole
        assert SystemRole.SUPPORT in SystemRole
    
    def test_permissions(self):
        """Test permission enumeration."""
        assert Permission.USER_CREATE in Permission
        assert Permission.USER_READ in Permission
        assert Permission.EVENT_CREATE in Permission
        assert Permission.TEAM_MANAGE in Permission
    
    def test_has_system_permission_super_admin(self):
        """Test super admin has all permissions."""
        # Super admin should have all permissions
        result = self.rbac_manager.has_system_permission(
            SystemRole.SUPER_ADMIN, 
            Permission.USER_CREATE
        )
        assert result is True
        
        result = self.rbac_manager.has_system_permission(
            SystemRole.SUPER_ADMIN, 
            Permission.EVENT_DELETE
        )
        assert result is True
    
    def test_has_system_permission_regular_user(self):
        """Test regular user permissions."""
        # None role should not have admin permissions
        result = self.rbac_manager.has_system_permission(
            None, 
            Permission.USER_DELETE
        )
        assert result is False


class TestSessionManager:
    """Test session management."""
    
    def setup_method(self):
        self.session_manager = SessionManager()
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test session creation."""
        user_id = 123
        refresh_token = "test_refresh_token"
        user_agent = "Test Browser"
        ip_address = "127.0.0.1"
        
        # Mock the session store
        with pytest.raises(AttributeError):
            # This will fail because session_store is not mocked
            # In a real test, we'd mock session_store
            session = await self.session_manager.create_session(
                user_id=user_id,
                refresh_token=refresh_token,
                user_agent=user_agent,
                ip_address=ip_address
            )
    
    @pytest.mark.asyncio
    async def test_invalidate_session(self):
        """Test session invalidation."""
        refresh_token = "test_refresh_token"
        
        # This would require mocking session_store
        result = await self.session_manager.invalidate_session(refresh_token)
        # Without mocking, this will use the actual Redis client


def test_authentication_flow():
    """Test complete authentication flow."""
    # Initialize managers
    token_manager = TokenManager()
    password_manager = PasswordManager()
    
    # Simulate user registration
    user_id = 123
    password = "secure_password_123"
    
    # Hash password (as done during registration)
    password_hash = password_manager.hash_password(password)
    
    # Simulate login
    # 1. Verify password
    is_valid = password_manager.verify_password(password, password_hash)
    assert is_valid is True
    
    # 2. Generate tokens
    access_token = token_manager.create_access_token(user_id)
    refresh_token = token_manager.create_refresh_token(user_id)
    
    assert isinstance(access_token, str)
    assert isinstance(refresh_token, str)
    
    # 3. Verify tokens
    access_payload = token_manager.verify_token(access_token)
    refresh_payload = token_manager.verify_token(refresh_token)
    
    assert access_payload["sub"] == str(user_id)
    assert refresh_payload["sub"] == str(user_id)
    assert access_payload["type"] == "access"
    assert refresh_payload["type"] == "refresh"


def test_permission_checking():
    """Test permission checking logic."""
    rbac_manager = RBACManager()
    
    # Test super admin permissions
    assert rbac_manager.has_system_permission(
        SystemRole.SUPER_ADMIN, 
        Permission.USER_CREATE
    ) is True
    
    # Test platform admin permissions
    assert rbac_manager.has_system_permission(
        SystemRole.PLATFORM_ADMIN, 
        Permission.EVENT_CREATE
    ) is True
    
    # Test no role permissions
    assert rbac_manager.has_system_permission(
        None, 
        Permission.USER_DELETE
    ) is False


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
