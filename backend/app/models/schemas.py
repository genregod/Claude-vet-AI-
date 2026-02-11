from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Veteran(BaseModel):
    id: Optional[str] = None
    name: str
    service_branch: str
    service_dates: Optional[str] = None
    discharge_status: Optional[str] = None
    email: str
    phone: Optional[str] = None
    created_at: Optional[datetime] = None

class Claim(BaseModel):
    id: Optional[str] = None
    veteran_id: str
    claim_type: str  # "initial" or "appeal"
    conditions: str  # Claimed conditions/disabilities
    service_connection: str  # How conditions relate to service
    evidence_description: Optional[str] = None
    ai_response: Optional[str] = None
    created_at: Optional[datetime] = None
