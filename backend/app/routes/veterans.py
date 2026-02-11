from fastapi import APIRouter, HTTPException
from app.models.schemas import Veteran
from typing import List
import uuid
from datetime import datetime

router = APIRouter()

# In-memory storage (for demo purposes)
veterans_db = {}

@router.get("/", response_model=List[Veteran])
async def get_veterans():
    """Get all veterans"""
    return list(veterans_db.values())

@router.get("/{veteran_id}", response_model=Veteran)
async def get_veteran(veteran_id: str):
    """Get a specific veteran"""
    if veteran_id not in veterans_db:
        raise HTTPException(status_code=404, detail="Veteran not found")
    return veterans_db[veteran_id]

@router.post("/", response_model=Veteran)
async def create_veteran(veteran: Veteran):
    """Create a new veteran profile"""
    veteran_id = str(uuid.uuid4())
    veteran.id = veteran_id
    veteran.created_at = datetime.now()
    veterans_db[veteran_id] = veteran
    return veteran

@router.put("/{veteran_id}", response_model=Veteran)
async def update_veteran(veteran_id: str, veteran: Veteran):
    """Update a veteran profile"""
    if veteran_id not in veterans_db:
        raise HTTPException(status_code=404, detail="Veteran not found")
    veteran.id = veteran_id
    veterans_db[veteran_id] = veteran
    return veteran

@router.delete("/{veteran_id}")
async def delete_veteran(veteran_id: str):
    """Delete a veteran profile"""
    if veteran_id not in veterans_db:
        raise HTTPException(status_code=404, detail="Veteran not found")
    del veterans_db[veteran_id]
    return {"message": "Veteran profile deleted successfully"}
