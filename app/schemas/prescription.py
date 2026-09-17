#app/schemas/prescription.py

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PrescriptionBase(BaseModel):
    title: str = "My Prescription"
    right_sph: Optional[float] = 0.0
    right_cyl: Optional[float] = 0.0
    right_axis: Optional[int] = 180
    left_sph: Optional[float] = 0.0
    left_cyl: Optional[float] = 0.0
    left_axis: Optional[int] = 180
    pd_mm: Optional[float] = 63.0
    file_url: Optional[str] = None
    is_default: bool = False

class PrescriptionCreate(PrescriptionBase):
    pass

class PrescriptionUpdate(BaseModel):
    title: Optional[str] = None
    right_sph: Optional[float] = None
    right_cyl: Optional[float] = None
    right_axis: Optional[int] = None
    left_sph: Optional[float] = None
    left_cyl: Optional[float] = None
    left_axis: Optional[int] = None
    pd_mm: Optional[float] = None
    file_url: Optional[str] = None
    is_default: Optional[bool] = None

class PrescriptionResponse(PrescriptionBase):
    id: int
    user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True