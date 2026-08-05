from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime

UK_COUNTRY_CODES = ["UK", "GB", "UNITED KINGDOM", "GREAT BRITAIN"]

class OrderCreate(BaseModel):
    product_id: int
    order_type: str  # "frame_only", "upload_prescription", "manual_prescription", "book_appointment"
    shipping_address: str
    country: str     # e.g., "UK", "NG", "US"

    # Appointment field (Required if order_type == "book_appointment")
    appointment_date: Optional[datetime] = None

    # Prescription fields (Used if order_type in ["upload_prescription", "manual_prescription"])
    prescription_file_url: Optional[str] = None
    right_sph: Optional[float] = None
    right_cyl: Optional[float] = None
    right_axis: Optional[int] = None
    left_sph: Optional[float] = None
    left_cyl: Optional[float] = None
    left_axis: Optional[int] = None
    pd_mm: Optional[float] = None

    @validator("order_type")
    def validate_order_type(cls, v):
        allowed = ["frame_only", "upload_prescription", "manual_prescription", "book_appointment"]
        if v not in allowed:
            raise ValueError(f"order_type must be one of {allowed}")
        return v

    @validator("country")
    def validate_country(cls, v, values):
        country_clean = v.strip().upper()
        order_type = values.get("order_type")

        # Restrict appointments strictly to UK customers
        if order_type == "book_appointment" and country_clean not in UK_COUNTRY_CODES:
            raise ValueError("In-clinic eye exam appointments are only available for UK addresses.")
        return v


class OrderResponse(BaseModel):
    id: int
    product_id: int
    order_type: str
    country: str
    shipping_address: str
    frame_price: float
    lens_fee: float
    exam_fee: float
    shipping_fee: float
    total_amount: float
    status: str
    appointment_date: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True