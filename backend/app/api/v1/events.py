"""
Events API endpoints
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def events_root():
    """Events endpoints root"""
    return {"message": "Events API v1"}