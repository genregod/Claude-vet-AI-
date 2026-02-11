from fastapi import APIRouter, HTTPException
from app.models.schemas import Claim
from app.services.claude_service import claude_service
from app.routes.veterans import veterans_db
from typing import List
import uuid
from datetime import datetime

router = APIRouter()

# In-memory storage (for demo purposes)
claims_db = {}

@router.get("/", response_model=List[Claim])
async def get_claims():
    """Get all claims"""
    return list(claims_db.values())

@router.get("/{claim_id}", response_model=Claim)
async def get_claim(claim_id: str):
    """Get a specific claim"""
    if claim_id not in claims_db:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claims_db[claim_id]

@router.post("/", response_model=Claim)
async def create_claim(claim: Claim):
    """Create a new claim and get AI assistance"""
    # Validate veteran exists
    if claim.veteran_id not in veterans_db:
        raise HTTPException(status_code=404, detail="Veteran not found")
    
    veteran = veterans_db[claim.veteran_id]
    
    # Get AI assistance
    veteran_info = {
        "name": veteran.name,
        "service_branch": veteran.service_branch,
        "service_dates": veteran.service_dates,
        "discharge_status": veteran.discharge_status
    }
    
    claim_details = {
        "claim_type": claim.claim_type,
        "conditions": claim.conditions,
        "service_connection": claim.service_connection,
        "evidence_description": claim.evidence_description
    }
    
    ai_response = await claude_service.get_claim_assistance(veteran_info, claim_details)
    
    # Save claim
    claim_id = str(uuid.uuid4())
    claim.id = claim_id
    claim.ai_response = ai_response
    claim.created_at = datetime.now()
    claims_db[claim_id] = claim
    
    return claim
