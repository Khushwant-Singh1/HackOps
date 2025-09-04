"""
Teams API endpoints
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def teams_root():
    """Teams endpoints root"""
    return {"message": "Teams API v1"}