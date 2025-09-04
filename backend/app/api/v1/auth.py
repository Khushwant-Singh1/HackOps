"""
Authentication API endpoints
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def auth_root():
    """Authentication endpoints root"""
    return {"message": "Authentication API v1"}