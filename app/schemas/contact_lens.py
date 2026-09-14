#app/schemas/contact_lens.py

from pydantic import BaseModel, Field, validator
from datetime import date
from typing import Optional

class EyeConfigSchema(BaseModel):
    sph: float = Field(..., description="Sphere / Power")
    cyl: Optional[float] = Field(None, description="Cylinder (Toric only)")
    axis: Optional[int] = Field(None, ge=1, le=180, description="Axis 1-180")
    add_power: Optional[str] = Field(None, description="LOW, MED, HIGH or numeric ADD")
    bc: float = Field(..., description="Base Curve")
    dia: float = Field(..., description="Diameter")
    boxes_quantity: int = Field(1, ge=0)

class ContactLensOrderCreate(BaseModel):
    product_id: int
    prescription_file_url: str
    expiry_date: date
    left_eye: Optional[EyeConfigSchema] = None
    right_eye: Optional[EyeConfigSchema] = None

    @validator("expiry_date")
    def validate_uk_legal_expiry(cls, v: date):
        if v < date.today():
            raise ValueError("Under UK Opticians Act regulations, contact lens prescriptions must be active and unexpired.")
        return v