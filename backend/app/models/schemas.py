from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Patient(BaseModel):
    id: Optional[str] = None
    name: str
    species: str
    breed: Optional[str] = None
    age: Optional[int] = None
    owner_name: str
    owner_contact: str
    created_at: Optional[datetime] = None

class Consultation(BaseModel):
    id: Optional[str] = None
    patient_id: str
    symptoms: str
    ai_response: Optional[str] = None
    created_at: Optional[datetime] = None
