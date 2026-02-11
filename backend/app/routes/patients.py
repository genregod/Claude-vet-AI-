from fastapi import APIRouter, HTTPException
from app.models.schemas import Patient
from typing import List
import uuid
from datetime import datetime

router = APIRouter()

# In-memory storage (for demo purposes)
patients_db = {}

@router.get("/", response_model=List[Patient])
async def get_patients():
    """Get all patients"""
    return list(patients_db.values())

@router.get("/{patient_id}", response_model=Patient)
async def get_patient(patient_id: str):
    """Get a specific patient"""
    if patient_id not in patients_db:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patients_db[patient_id]

@router.post("/", response_model=Patient)
async def create_patient(patient: Patient):
    """Create a new patient"""
    patient_id = str(uuid.uuid4())
    patient.id = patient_id
    patient.created_at = datetime.now()
    patients_db[patient_id] = patient
    return patient

@router.put("/{patient_id}", response_model=Patient)
async def update_patient(patient_id: str, patient: Patient):
    """Update a patient"""
    if patient_id not in patients_db:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.id = patient_id
    patients_db[patient_id] = patient
    return patient

@router.delete("/{patient_id}")
async def delete_patient(patient_id: str):
    """Delete a patient"""
    if patient_id not in patients_db:
        raise HTTPException(status_code=404, detail="Patient not found")
    del patients_db[patient_id]
    return {"message": "Patient deleted successfully"}
