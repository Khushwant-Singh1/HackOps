"""
Submissions API endpoints
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def submissions_root():
    """Submissions endpoints root"""
    return {"message": "Submissions API v1"}