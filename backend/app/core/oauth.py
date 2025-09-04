"""
OAuth Integration Services

This module provides OAuth integration with multiple providers:
- Google OAuth 2.0
- GitHub OAuth 2.0  
- Microsoft Azure AD / OAuth 2.0
- Generic OIDC support
"""

import asyncio
import httpx
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode
from dataclasses import dataclass

from app.core.config import settings

@dataclass
class OAuthUserInfo:
    """Standardized OAuth user information."""
    provider: str
    oauth_id: str
    email: str
    first_name: str
    last_name: str
    avatar_url: Optional[str] = None
    profile_url: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None

class OAuthProvider:
    """Base OAuth provider class."""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.http_client = httpx.AsyncClient()
    
    async def get_authorization_url(self, state: str, scopes: List[str] = None) -> str:
        """Generate OAuth authorization URL."""
        raise NotImplementedError
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        raise NotImplementedError
    
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user information from OAuth provider."""
        raise NotImplementedError
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an OAuth token."""
        raise NotImplementedError
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke an OAuth token."""
        raise NotImplementedError

class GoogleOAuthProvider(OAuthProvider):
    """Google OAuth 2.0 provider."""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(client_id, client_secret, redirect_uri)
        self.auth_url = "https://accounts.google.com/o/oauth2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        self.revoke_url = "https://oauth2.googleapis.com/revoke"
    
    async def get_authorization_url(self, state: str, scopes: List[str] = None) -> str:
        """Generate Google OAuth authorization URL."""
        if scopes is None:
            scopes = ["openid", "email", "profile"]
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(scopes),
            "response_type": "code",
            "state": state,
            "access_type": "offline",
            "prompt": "consent"
        }
        
        return f"{self.auth_url}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for Google access token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri
        }
        
        response = await self.http_client.post(self.token_url, data=data)
        response.raise_for_status()
        return response.json()
    
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user information from Google."""
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await self.http_client.get(self.userinfo_url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        return OAuthUserInfo(
            provider="google",
            oauth_id=data["id"],
            email=data["email"],
            first_name=data.get("given_name", ""),
            last_name=data.get("family_name", ""),
            avatar_url=data.get("picture"),
            raw_data=data
        )
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh Google OAuth token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        response = await self.http_client.post(self.token_url, data=data)
        response.raise_for_status()
        return response.json()
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke Google OAuth token."""
        params = {"token": token}
        response = await self.http_client.post(self.revoke_url, params=params)
        return response.status_code == 200

class GitHubOAuthProvider(OAuthProvider):
    """GitHub OAuth 2.0 provider."""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(client_id, client_secret, redirect_uri)
        self.auth_url = "https://github.com/login/oauth/authorize"
        self.token_url = "https://github.com/login/oauth/access_token"
        self.userinfo_url = "https://api.github.com/user"
        self.emails_url = "https://api.github.com/user/emails"
    
    async def get_authorization_url(self, state: str, scopes: List[str] = None) -> str:
        """Generate GitHub OAuth authorization URL."""
        if scopes is None:
            scopes = ["user:email"]
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(scopes),
            "state": state
        }
        
        return f"{self.auth_url}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for GitHub access token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        
        headers = {"Accept": "application/json"}
        response = await self.http_client.post(self.token_url, data=data, headers=headers)
        response.raise_for_status()
        return response.json()
    
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user information from GitHub."""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Get user profile
        response = await self.http_client.get(self.userinfo_url, headers=headers)
        response.raise_for_status()
        user_data = response.json()
        
        # Get primary email
        email_response = await self.http_client.get(self.emails_url, headers=headers)
        email_response.raise_for_status()
        emails = email_response.json()
        
        primary_email = None
        for email in emails:
            if email.get("primary", False):
                primary_email = email["email"]
                break
        
        if not primary_email and emails:
            primary_email = emails[0]["email"]
        
        # Parse name
        full_name = user_data.get("name", "").split(" ", 1)
        first_name = full_name[0] if full_name else ""
        last_name = full_name[1] if len(full_name) > 1 else ""
        
        return OAuthUserInfo(
            provider="github",
            oauth_id=str(user_data["id"]),
            email=primary_email or "",
            first_name=first_name,
            last_name=last_name,
            avatar_url=user_data.get("avatar_url"),
            profile_url=user_data.get("html_url"),
            raw_data=user_data
        )
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """GitHub doesn't support refresh tokens - tokens don't expire."""
        raise NotImplementedError("GitHub access tokens do not expire")
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke GitHub OAuth token."""
        # GitHub uses app-specific token revocation
        revoke_url = f"https://api.github.com/applications/{self.client_id}/token"
        auth = (self.client_id, self.client_secret)
        data = {"access_token": token}
        
        response = await self.http_client.delete(revoke_url, json=data, auth=auth)
        return response.status_code == 204

class MicrosoftOAuthProvider(OAuthProvider):
    """Microsoft Azure AD OAuth 2.0 provider."""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, tenant: str = "common"):
        super().__init__(client_id, client_secret, redirect_uri)
        self.tenant = tenant
        self.auth_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
        self.token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        self.userinfo_url = "https://graph.microsoft.com/v1.0/me"
    
    async def get_authorization_url(self, state: str, scopes: List[str] = None) -> str:
        """Generate Microsoft OAuth authorization URL."""
        if scopes is None:
            scopes = ["openid", "profile", "email", "User.Read"]
        
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "response_mode": "query"
        }
        
        return f"{self.auth_url}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for Microsoft access token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri
        }
        
        response = await self.http_client.post(self.token_url, data=data)
        response.raise_for_status()
        return response.json()
    
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user information from Microsoft Graph."""
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await self.http_client.get(self.userinfo_url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        return OAuthUserInfo(
            provider="microsoft",
            oauth_id=data["id"],
            email=data.get("mail") or data.get("userPrincipalName", ""),
            first_name=data.get("givenName", ""),
            last_name=data.get("surname", ""),
            raw_data=data
        )
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh Microsoft OAuth token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        response = await self.http_client.post(self.token_url, data=data)
        response.raise_for_status()
        return response.json()
    
    async def revoke_token(self, token: str) -> bool:
        """Microsoft doesn't provide a standard revoke endpoint."""
        # Microsoft tokens expire automatically
        return True

class OAuthManager:
    """Manages multiple OAuth providers."""
    
    def __init__(self):
        self.providers: Dict[str, OAuthProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize OAuth providers based on configuration."""
        base_redirect_uri = f"{settings.BASE_URL}/api/v1/auth/callback"
        
        # Google OAuth
        if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
            self.providers["google"] = GoogleOAuthProvider(
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                redirect_uri=f"{base_redirect_uri}/google"
            )
        
        # GitHub OAuth
        if settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET:
            self.providers["github"] = GitHubOAuthProvider(
                client_id=settings.GITHUB_CLIENT_ID,
                client_secret=settings.GITHUB_CLIENT_SECRET,
                redirect_uri=f"{base_redirect_uri}/github"
            )
        
        # Microsoft OAuth
        if settings.MICROSOFT_CLIENT_ID and settings.MICROSOFT_CLIENT_SECRET:
            self.providers["microsoft"] = MicrosoftOAuthProvider(
                client_id=settings.MICROSOFT_CLIENT_ID,
                client_secret=settings.MICROSOFT_CLIENT_SECRET,
                redirect_uri=f"{base_redirect_uri}/microsoft"
            )
    
    def get_provider(self, provider_name: str) -> Optional[OAuthProvider]:
        """Get OAuth provider by name."""
        return self.providers.get(provider_name)
    
    def get_available_providers(self) -> List[str]:
        """Get list of available OAuth providers."""
        return list(self.providers.keys())
    
    async def get_authorization_url(self, provider_name: str, state: str) -> Optional[str]:
        """Get authorization URL for a provider."""
        provider = self.get_provider(provider_name)
        if provider:
            return await provider.get_authorization_url(state)
        return None
    
    async def exchange_code_for_token(self, provider_name: str, code: str) -> Optional[Dict[str, Any]]:
        """Exchange code for token with a provider."""
        provider = self.get_provider(provider_name)
        if provider:
            return await provider.exchange_code_for_token(code)
        return None
    
    async def get_user_info(self, provider_name: str, access_token: str) -> Optional[OAuthUserInfo]:
        """Get user info from a provider."""
        provider = self.get_provider(provider_name)
        if provider:
            return await provider.get_user_info(access_token)
        return None

# Global OAuth manager instance
oauth_manager = OAuthManager()
