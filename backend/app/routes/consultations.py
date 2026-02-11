from fastapi import APIRouter, HTTPException
from app.models.schemas import Consultation
from app.services.claude_service import claude_service
from app.routes.patients import patients_db
from typing import List
import uuid
from datetime import datetime

router = APIRouter()

# In-memory storage (for demo purposes)
consultations_db = {}

@router.get("/", response_model=List[Consultation])
async def get_consultations():
    """Get all consultations"""
    return list(consultations_db.values())

@router.get("/{consultation_id}", response_model=Consultation)
async def get_consultation(consultation_id: str):
    """Get a specific consultation"""
    if consultation_id not in consultations_db:
        raise HTTPException(status_code=404, detail="Consultation not found")
    return consultations_db[consultation_id]

@router.post("/", response_model=Consultation)
async def create_consultation(consultation: Consultation):
    """Create a new consultation and get AI response"""
    # Validate patient exists
    if consultation.patient_id not in patients_db:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    patient = patients_db[consultation.patient_id]
    
    # Get AI consultation
    patient_info = {
        "name": patient.name,
        "species": patient.species,
        "breed": patient.breed,
        "age": patient.age
    }
    
    ai_response = await claude_service.get_consultation(patient_info, consultation.symptoms)
    
    # Save consultation
    consultation_id = str(uuid.uuid4())
    consultation.id = consultation_id
    consultation.ai_response = ai_response
    consultation.created_at = datetime.now()
    consultations_db[consultation_id] = consultation
    
    return consultation
